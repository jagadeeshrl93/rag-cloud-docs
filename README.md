# RAG Cloud Docs

> Production-grade Retrieval-Augmented Generation (RAG) system
> for querying cloud infrastructure documentation using natural language.

---

## What this is

A RAG system that answers questions about cloud infrastructure documents
(runbooks, incident post-mortems, SOPs) using hybrid retrieval and a
local or cloud LLM.

Ask it: _"How do I rotate AWS IAM credentials?"_
It finds the right sections from your documents and writes a precise answer
citing the source — no hallucination, no guessing.

---

## Architecture

```
Question → FastAPI → Hybrid Search → LLM → Answer
                         ↓
              Vector Search (ChromaDB)
                    +
              Keyword Search (BM25)
                    ↓
           Reciprocal Rank Fusion (RRF)
```

| Component       | Technology                            |
| --------------- | ------------------------------------- |
| Document loader | PyMuPDF, BeautifulSoup4               |
| Chunking        | Recursive character splitter          |
| Embeddings      | sentence-transformers (local)         |
| Vector store    | ChromaDB                              |
| Keyword search  | rank-bm25                             |
| Result merging  | Reciprocal Rank Fusion (RRF)          |
| LLM             | Ollama llama3.2 (local) / GPT-4o-mini |
| API             | FastAPI + Pydantic                    |
| Frontend        | Streamlit                             |

---

## Evaluation

This system is evaluated using [RAGAS](https://github.com/explodinggradients/ragas)
— a framework that measures RAG quality across four dimensions.

### Metrics

| Metric            | What it measures                                                            | Score |
| ----------------- | --------------------------------------------------------------------------- | ----- |
| Faithfulness      | Does the answer stick to what the documents say, or does it make things up? | TBD   |
| Answer relevancy  | Does the answer actually address the question asked?                        | TBD   |
| Context recall    | Did retrieval find the right chunks for the question?                       | TBD   |
| Context precision | Were the retrieved chunks actually useful, or was there noise?              | TBD   |

_Scores are between 0 and 1. Above 0.8 is good. Above 0.9 is excellent._

_Run `make eval` to reproduce these results._

### Eval dataset

28 question/answer pairs hand-written from the domain documents.
Located in `eval/dataset.json`.

---

## Key design decisions

**Why hybrid retrieval?**
Pure vector search misses exact terms like flag names, error codes, and
version numbers. BM25 handles these precisely. Combining both with RRF
fusion gives the best of semantic understanding and exact keyword matching.

**Why build the chunker from scratch?**
Understanding chunk boundaries matters — a step without its preceding
explanation produces bad answers. Building it from scratch meant making
a conscious decision about chunk size (512 tokens) and overlap (50 tokens)
rather than accepting a framework default.

**Why Ollama for local inference?**
Zero cost, no API key needed, runs entirely on your machine. The system
automatically falls back to Ollama if no OpenAI key is configured —
making it easy to develop and demo without spending money.

---

## Getting started

### Prerequisites

- Python 3.11
- [Ollama](https://ollama.com) for free local inference

### Setup

```bash
git clone https://github.com/jagadeeshrl93/rag-cloud-docs
cd rag-cloud-docs

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn pydantic pydantic-settings \
            chromadb openai pymupdf beautifulsoup4 \
            rank-bm25 sentence-transformers httpx python-dotenv

cp .env.example .env
```

### Add your documents

Drop PDF, Markdown, or text files into the `data/` folder.

### Start Ollama (free local LLM)

```bash
ollama serve            # terminal 1
ollama pull llama3.2
```

### Run the API

```bash
uvicorn src.api.main:app --reload    # terminal 2
```

### Run the frontend

```bash
streamlit run frontend/app.py        # terminal 3
```

Open http://localhost:8501 in your browser.

### Ingest your documents

Click **Ingest documents** in the sidebar, then ask a question.

---

## API reference

### POST /ingest

```json
{
  "directory": "data",
  "clear_existing": true
}
```

### POST /query

```json
{
  "question": "How do I rotate AWS IAM credentials?",
  "top_k": 5
}
```

Response includes `answer`, `sources`, `model`, and `chunks_used`.

---

## Project structure

```
src/
├── config.py           settings and environment variables
├── ingestion/
│   ├── loader.py       document loading (PDF, Markdown, HTML)
│   ├── chunker.py      recursive character splitter
│   └── embedder.py     embeddings + ChromaDB storage
├── retrieval/
│   ├── vector_store.py semantic search via ChromaDB
│   ├── bm25.py         keyword search via BM25
│   └── hybrid.py       RRF fusion of both results
├── generation/
│   └── llm.py          LLM routing (Ollama / OpenAI / mock)
└── api/
    ├── main.py         FastAPI app entry point
    ├── routes.py       /ingest and /query endpoints
    └── schemas.py      Pydantic request/response models
frontend/
└── app.py              Streamlit chat UI
eval/
└── dataset.json        RAGAS evaluation dataset
```

---

## What I'd build next

- [ ] RAGAS evaluation scores — run eval harness and update table above
- [ ] Cross-encoder reranking on top of RRF results
- [ ] Migrate vector store to pgvector on AWS RDS
- [ ] Dockerfile + AWS deployment on EC2 free tier
- [ ] Conversation memory for multi-turn Q&A
- [ ] Support for more document types (DOCX, Confluence, Notion)

---

## Example output

**Question:** How do I rotate AWS IAM credentials?

**Answer:** According to [Source 1: aws-runbook.md], you should rotate
AWS access keys every 90 days as standard policy, immediately if a key
is suspected compromised, and when an engineer leaves the team...

---

_Built by Jagadeesh Reddy — Senior Platform & Cloud AI Engineer_
_GitHub: [jagadeeshrl93](https://github.com/jagadeeshrl93)_
