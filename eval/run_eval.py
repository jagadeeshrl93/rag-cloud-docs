import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRecall, ContextPrecision
from openai import OpenAI as OpenAIClient
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory

from src.retrieval.hybrid import hybrid_search
from src.generation.llm import generate_answer
from src.config import settings


def run_evaluation(
    dataset_path: str = "eval/dataset.json",
    output_path: str = "eval/results/latest.json",
    sample_size: int = None,
):
    # Load eval dataset
    with open(dataset_path) as f:
        dataset = json.load(f)

    if sample_size:
        dataset = dataset[:sample_size]

    print(f"Running eval on {len(dataset)} questions...")

    questions = []
    ground_truths = []
    answers = []
    contexts = []

    for i, item in enumerate(dataset):
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"[{i+1}/{len(dataset)}] {question[:60]}...")

        # Retrieve chunks directly from ChromaDB — bypass get_collection
        # to avoid embedding function conflict
        import chromadb
        from chromadb.utils import embedding_functions

        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        collection = client.get_collection(name="rag_docs")
        
        # Query using the collection directly
        results = collection.query(
            query_texts=[question],
            n_results=min(5, collection.count()),
            include=["documents", "metadatas"],
        )
        
        context_texts = results["documents"][0]
        metadatas = results["metadatas"][0]
        
        chunks = []
        for text, meta in zip(context_texts, metadatas):
            chunks.append({
                "text": text,
                "source": meta["source"],
                "chunk_index": meta["chunk_index"],
            })

        # Generate answer
        result = generate_answer(question, chunks)
        answer = result["answer"]

        questions.append(question)
        ground_truths.append(ground_truth)
        answers.append(answer)
        contexts.append(context_texts)

    # Build RAGAS dataset
    ragas_dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    # Configure RAGAS to use OpenAI
    openai_client = OpenAIClient(api_key=settings.openai_api_key)
    llm = llm_factory("gpt-4o-mini", client=openai_client)
    embeddings = embedding_factory(
        "openai",
        model="text-embedding-3-small",
        client=openai_client,
    )

    # Instantiate metrics
    metrics = [
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextRecall(llm=llm),
        ContextPrecision(llm=llm),
    ]

    # Run evaluation
    print("\nScoring with RAGAS...")
    results = evaluate(
        dataset=ragas_dataset,
        metrics=metrics,
    )

    # Print results
    print("\n" + "="*50)
    print("RAGAS EVALUATION RESULTS")
    print("="*50)
    scores = results.to_pandas()

    metrics = {
        "faithfulness": float(scores["faithfulness"].mean()),
        "answer_relevancy": float(scores["answer_relevancy"].mean()),
        "context_recall": float(scores["context_recall"].mean()),
        "context_precision": float(scores["context_precision"].mean()),
    }

    for metric, score in metrics.items():
        bar = "█" * int(score * 20)
        print(f"{metric:<25} {score:.3f}  {bar}")

    print("="*50)

    # Save results
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nResults saved to {output_path}")
    print("\nCopy these scores into your README.md evaluation table.")
    return metrics


if __name__ == "__main__":
    run_evaluation()