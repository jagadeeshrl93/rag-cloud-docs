import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.api.schemas import IngestRequest, IngestResponse, QueryRequest, QueryResponse
from src.ingestion.loader import load_documents_from_dir
from src.ingestion.chunker import chunk_documents
from src.ingestion.embedder import embed_chunks
from src.retrieval.hybrid import hybrid_search
from src.generation.llm import generate_answer
from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest):
    """Load documents from a directory, chunk them, and store embeddings."""
    directory = Path(request.directory)

    if not directory.exists():
        raise HTTPException(status_code=400, detail=f"Directory not found: {directory}")

    try:
        docs = load_documents_from_dir(directory)
        if not docs:
            raise HTTPException(status_code=400, detail="No supported documents found in directory")

        chunks = chunk_documents(docs, settings.chunk_size, settings.chunk_overlap)
        collection = embed_chunks(chunks, clear_existing=request.clear_existing)

        return IngestResponse(
            message="Ingestion complete",
            chunks_stored=collection.count(),
            documents_loaded=len(docs),
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """Search the knowledge base and generate an answer."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        chunks = hybrid_search(
            query=request.question,
            top_k=request.top_k,
        )

        if not chunks:
            return QueryResponse(
                answer="No relevant information found in the knowledge base.",
                sources=[],
                model="none",
                chunks_used=0,
            )

        result = generate_answer(
            query=request.question,
            chunks=chunks,
        )

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            model=result["model"],
            chunks_used=len(chunks),
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))