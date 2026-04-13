# ── Stage 1: dependency builder ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools needed by some Python packages (e.g. sentence-transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime image ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY src/       ./src/
COPY frontend/  ./frontend/
COPY data/      ./data/

# Sentence-transformers downloads model weights on first run; cache them here
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers
ENV TRANSFORMERS_CACHE=/app/.cache/transformers
# Keep Python output unbuffered for clean Docker logs
ENV PYTHONUNBUFFERED=1
# ChromaDB persistent directory (overridable at runtime)
ENV CHROMA_PERSIST_DIR=/app/.chroma

# Create directories that are mounted as volumes
RUN mkdir -p /app/.chroma /app/data /app/.cache

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
