import logging
import os

import chromadb
from chromadb.utils import embedding_functions
from src.config import settings

logger = logging.getLogger(__name__)


def get_embedding_function():
    """
    Returns the embedding function.
    Uses OpenAI if API key is set, otherwise falls back to a
    lightweight local model via sentence-transformers (free).
    """
    if settings.openai_api_key and settings.openai_api_key != "sk-your-key-here":
        logger.info("Using OpenAI embeddings (text-embedding-3-small)")
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small",
        )
    else:
        logger.info("Using local embeddings (all-MiniLM-L6-v2) — free, no API key needed")
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )


def get_collection(collection_name: str = "rag_docs") -> chromadb.Collection:
    """
    Connect to ChromaDB and return the collection.
    Creates the collection if it doesn't exist.
    """
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embedding_fn = get_embedding_function()

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def embed_chunks(
    chunks: list[dict],
    collection_name: str = "rag_docs",
    clear_existing: bool = False,
) -> chromadb.Collection:
    """
    Embed a list of chunks and store them in ChromaDB.

    Args:
        chunks: list of {'text': ..., 'source': ..., 'chunk_index': ...}
        collection_name: ChromaDB collection to store in
        clear_existing: if True, wipe the collection before inserting

    Returns:
        The ChromaDB collection with all chunks stored
    """
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embedding_fn = get_embedding_function()

    # Wipe and recreate if requested — prevents duplicate chunks on re-ingest
    if clear_existing:
        try:
            client.delete_collection(collection_name)
            logger.info(f"Cleared existing collection: {collection_name}")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # Build parallel lists — ChromaDB expects these as separate arrays
    ids = []
    texts = []
    metadatas = []

    for chunk in chunks:
        chunk_id = f"{chunk['source']}__chunk_{chunk['chunk_index']}"
        ids.append(chunk_id)
        texts.append(chunk["text"])
        metadatas.append({
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"],
        })

    # Insert in batches of 100 to avoid memory issues with large doc sets
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_texts = texts[i:i + batch_size]
        batch_metadatas = metadatas[i:i + batch_size]

        collection.upsert(
            ids=batch_ids,
            documents=batch_texts,
            metadatas=batch_metadatas,
        )
        logger.info(f"Embedded batch {i // batch_size + 1} — {len(batch_ids)} chunks")

    logger.info(f"Total chunks stored in ChromaDB: {collection.count()}")
    return collection