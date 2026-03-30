import logging

logger = logging.getLogger(__name__)


def count_tokens(text: str) -> int:
    """
    Rough token count — 1 token ≈ 4 characters.
    Avoids importing tiktoken as a dependency.
    """
    return len(text) // 4


def split_into_chunks(
    text: str,
    source: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[dict]:
    """
    Split text into overlapping chunks using recursive character splitting.
    Returns a list of dicts with 'text', 'source', and 'chunk_index' keys.
    """
    # Separators in priority order — try to split at natural boundaries
    separators = ["\n\n", "\n", ". ", " ", ""]

    chunks = _recursive_split(text, chunk_size, chunk_overlap, separators)

    result = []
    for i, chunk_text in enumerate(chunks):
        cleaned = chunk_text.strip()
        if not cleaned:
            continue
        result.append({
            "text": cleaned,
            "source": source,
            "chunk_index": i,
        })

    logger.info(f"Split '{source}' into {len(result)} chunks")
    return result


def _recursive_split(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[str]:
    """
    Recursively split text by trying separators in order.
    Falls back to the next separator if chunks are still too large.
    """
    if not separators:
        return _split_by_size(text, chunk_size, chunk_overlap)

    separator = separators[0]
    remaining_separators = separators[1:]

    # If text already fits in one chunk, return it as-is
    if count_tokens(text) <= chunk_size:
        return [text]

    # Split by current separator
    if separator:
        splits = text.split(separator)
    else:
        splits = list(text)

    chunks = []
    current_chunk = ""

    for split in splits:
        candidate = current_chunk + separator + split if current_chunk else split

        if count_tokens(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            # Current chunk is full — save it
            if current_chunk:
                chunks.append(current_chunk)

            # If this single split is still too large, recurse
            if count_tokens(split) > chunk_size:
                sub_chunks = _recursive_split(
                    split, chunk_size, chunk_overlap, remaining_separators
                )
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                current_chunk = split

    if current_chunk:
        chunks.append(current_chunk)

    # Apply overlap — carry the end of each chunk into the start of the next
    if chunk_overlap > 0 and len(chunks) > 1:
        chunks = _apply_overlap(chunks, chunk_overlap)

    return chunks


def _split_by_size(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Hard split by character count when no separator works."""
    char_size = chunk_size * 4
    char_overlap = chunk_overlap * 4
    chunks = []
    start = 0

    while start < len(text):
        end = start + char_size
        chunks.append(text[start:end])
        start += char_size - char_overlap

    return chunks


def _apply_overlap(chunks: list[str], overlap_tokens: int) -> list[str]:
    """Prepend the tail of each chunk to the start of the next."""
    overlap_chars = overlap_tokens * 4
    overlapped = [chunks[0]]

    for i in range(1, len(chunks)):
        tail = chunks[i - 1][-overlap_chars:]
        overlapped.append(tail + " " + chunks[i])

    return overlapped


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[dict]:
    """
    Chunk a list of loaded documents.
    Input: list of {'text': ..., 'source': ...}
    Output: list of {'text': ..., 'source': ..., 'chunk_index': ...}
    """
    all_chunks = []
    for doc in documents:
        chunks = split_into_chunks(
            text=doc["text"],
            source=doc["source"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(chunks)

    logger.info(f"Total chunks across all documents: {len(all_chunks)}")
    return all_chunks