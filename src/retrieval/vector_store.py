import logging

from src.ingestion.embedder import get_collection

logger = logging.getLogger(__name__)


def vector_search(
    query: str,
    top_k: int = 10,
    collection_name: str = "rag_docs",
) -> list[dict]:
    """
    Search ChromaDB for chunks semantically similar to the query.

    Returns a list of dicts with 'text', 'source', 'chunk_index', 'score'.
    """
    collection = get_collection(collection_name)

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, distance in zip(documents, metadatas, distances):
        # ChromaDB returns cosine distance (0=identical, 2=opposite)
        # Convert to similarity score (1=identical, 0=opposite)
        similarity = 1 - (distance / 2)
        hits.append({
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "score": round(similarity, 4),
            "retrieval_method": "vector",
        })

    logger.info(f"Vector search returned {len(hits)} results for: '{query[:50]}'")
    return hits