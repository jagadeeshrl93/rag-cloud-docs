import logging
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

from src.ingestion.embedder import get_collection

logger = logging.getLogger(__name__)

# Cache file so we don't rebuild the index on every query
BM25_CACHE_PATH = Path(".bm25_cache.pkl")


def build_bm25_index(
    collection_name: str = "rag_docs",
) -> tuple[BM25Okapi, list[dict]]:
    """
    Build a BM25 index from all chunks in ChromaDB.
    Returns the index and the list of all chunks.
    """
    collection = get_collection(collection_name)

    # Fetch all documents from ChromaDB
    all_data = collection.get(include=["documents", "metadatas"])
    documents = all_data["documents"]
    metadatas = all_data["metadatas"]

    chunks = []
    tokenized_corpus = []

    for doc, meta in zip(documents, metadatas):
        chunks.append({
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
        })
        # Tokenize by splitting on whitespace — simple and effective for BM25
        tokenized_corpus.append(doc.lower().split())

    index = BM25Okapi(tokenized_corpus)
    logger.info(f"Built BM25 index over {len(chunks)} chunks")
    return index, chunks


def bm25_search(
    query: str,
    top_k: int = 10,
    collection_name: str = "rag_docs",
) -> list[dict]:
    """
    Search chunks using BM25 keyword matching.

    Returns a list of dicts with 'text', 'source', 'chunk_index', 'score'.
    """
    index, chunks = build_bm25_index(collection_name)

    tokenized_query = query.lower().split()
    scores = index.get_scores(tokenized_query)

    # Pair each chunk with its score and sort
    scored = sorted(
        zip(scores, chunks),
        key=lambda x: x[0],
        reverse=True,
    )

    hits = []
    for score, chunk in scored[:top_k]:
        if score == 0:
            continue  # skip chunks with zero keyword overlap
        hits.append({
            "text": chunk["text"],
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"],
            "score": round(float(score), 4),
            "retrieval_method": "bm25",
        })

    logger.info(f"BM25 search returned {len(hits)} results for: '{query[:50]}'")
    return hits