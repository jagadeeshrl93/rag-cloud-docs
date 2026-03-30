import logging

from src.retrieval.vector_store import vector_search
from src.retrieval.bm25 import bm25_search

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    result_lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """
    Merge multiple ranked result lists using Reciprocal Rank Fusion.

    RRF score = sum of 1 / (k + rank) across all lists.
    Higher score = appeared higher in more lists.
    k=60 is the standard default from the original RRF paper.
    """
    scores: dict[str, float] = {}
    chunks: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, chunk in enumerate(result_list, start=1):
            # Use source + chunk_index as unique key
            key = f"{chunk['source']}__chunk_{chunk['chunk_index']}"
            scores[key] = scores.get(key, 0) + 1 / (k + rank)
            chunks[key] = chunk

    # Sort by RRF score descending
    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)

    merged = []
    for key in sorted_keys:
        chunk = chunks[key].copy()
        chunk["rrf_score"] = round(scores[key], 6)
        merged.append(chunk)

    return merged


def hybrid_search(
    query: str,
    top_k: int = 5,
    collection_name: str = "rag_docs",
    fetch_k: int = 10,
) -> list[dict]:
    """
    Run vector + BM25 search in parallel and merge with RRF.

    Args:
        query: the user's question
        top_k: number of final results to return
        collection_name: ChromaDB collection to search
        fetch_k: how many results to fetch from each engine before merging

    Returns:
        Top-k merged and reranked chunks
    """
    logger.info(f"Running hybrid search for: '{query[:60]}'")

    # Run both search engines
    vector_results = vector_search(query, top_k=fetch_k, collection_name=collection_name)
    bm25_results = bm25_search(query, top_k=fetch_k, collection_name=collection_name)

    logger.info(f"Vector: {len(vector_results)} results, BM25: {len(bm25_results)} results")

    # Merge with RRF
    merged = reciprocal_rank_fusion([vector_results, bm25_results])

    # Return top_k
    final = merged[:top_k]

    logger.info(f"Hybrid search returning {len(final)} merged results")
    return final