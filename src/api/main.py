import logging

from fastapi import FastAPI
from src.api.routes import router

logging.basicConfig(level=logging.WARNING)

app = FastAPI(
    title="RAG Cloud Docs",
    description="Ask questions about your cloud infrastructure documentation",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}