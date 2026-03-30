import logging

from src.config import settings

logger = logging.getLogger(__name__)


def build_prompt(query: str, chunks: list[dict]) -> str:
    """Build the prompt with retrieved chunks as context."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['source']}]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are a helpful cloud infrastructure assistant.
Answer the question using ONLY the context provided below.
If the answer is not in the context, say "I don't have that information in the provided documents."
Always mention which source your answer came from.

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:"""
    return prompt


def generate_answer_ollama(query: str, chunks: list[dict]) -> dict:
    """Generate answer using Ollama running locally — completely free."""
    import httpx

    prompt = build_prompt(query, chunks)

    try:
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        answer = response.json()["response"].strip()
        sources = list({c["source"] for c in chunks})

        return {
            "answer": answer,
            "sources": sources,
            "model": "ollama/llama3.2",
        }
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        raise


def generate_answer_openai(query: str, chunks: list[dict]) -> dict:
    """Generate answer using OpenAI API."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = build_prompt(query, chunks)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a precise cloud infrastructure assistant. "
                           "Answer only from the provided context. Be concise and accurate."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=500,
    )

    answer = response.choices[0].message.content.strip()
    sources = list({c["source"] for c in chunks})

    return {
        "answer": answer,
        "sources": sources,
        "model": "gpt-4o-mini",
    }


def generate_answer(query: str, chunks: list[dict]) -> dict:
    """
    Route to the right LLM based on what's configured.
    Priority: OpenAI (if key set) → Ollama (free, local) → Mock
    """
    has_openai_key = (
        settings.openai_api_key and
        settings.openai_api_key != "sk-your-key-here"
    )

    if has_openai_key:
        logger.info("Using OpenAI gpt-4o-mini")
        return generate_answer_openai(query, chunks)

    # Check if Ollama is running
    try:
        import httpx
        httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        logger.info("Using Ollama llama3.2 (local, free)")
        return generate_answer_ollama(query, chunks)
    except Exception:
        pass

    # Final fallback — mock
    logger.warning("No LLM available — returning mock answer. Start Ollama or add OpenAI key.")
    sources = list({c["source"] for c in chunks})
    return {
        "answer": (
            "No LLM configured. Either:\n"
            "1. Run 'ollama serve' in a terminal and 'ollama pull llama3.2'\n"
            "2. Add your OPENAI_API_KEY to .env"
        ),
        "sources": sources,
        "model": "mock",
    }