from pydantic import BaseModel


class IngestRequest(BaseModel):
    directory: str = "data"
    clear_existing: bool = True


class IngestResponse(BaseModel):
    message: str
    chunks_stored: int
    documents_loaded: int


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    model: str
    chunks_used: int