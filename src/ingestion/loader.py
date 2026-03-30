import logging
from pathlib import Path

import fitz  # PyMuPDF
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def load_pdf(file_path: Path) -> str:
    """Extract text from a PDF file."""
    doc = fitz.open(str(file_path))
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    logger.info(f"Loaded PDF: {file_path.name} ({len(doc)} pages)")
    return text


def load_markdown(file_path: Path) -> str:
    """Read a markdown or plain text file."""
    text = file_path.read_text(encoding="utf-8")
    logger.info(f"Loaded markdown: {file_path.name}")
    return text


def load_html(file_path: Path) -> str:
    """Extract text from an HTML file."""
    html = file_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    logger.info(f"Loaded HTML: {file_path.name}")
    return text


def load_document(file_path: Path) -> str:
    """Load any supported document type."""
    suffix = file_path.suffix.lower()

    loaders = {
        ".pdf": load_pdf,
        ".md": load_markdown,
        ".txt": load_markdown,
        ".html": load_html,
        ".htm": load_html,
    }

    if suffix not in loaders:
        raise ValueError(f"Unsupported file type: {suffix}")

    return loaders[suffix](file_path)


def load_documents_from_dir(directory: Path) -> list[dict]:
    """
    Load all supported documents from a directory.
    Returns a list of dicts with 'text' and 'source' keys.
    """
    supported = {".pdf", ".md", ".txt", ".html", ".htm"}
    documents = []

    for file_path in sorted(directory.iterdir()):
        if file_path.suffix.lower() not in supported:
            continue
        try:
            text = load_document(file_path)
            if text.strip():
                documents.append({
                    "text": text,
                    "source": file_path.name
                })
                logger.info(f"Loaded: {file_path.name} ({len(text)} chars)")
            else:
                logger.warning(f"Empty document skipped: {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to load {file_path.name}: {e}")

    return documents