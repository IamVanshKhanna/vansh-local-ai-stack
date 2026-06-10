"""Unified text extraction for RAG — PDF, DOCX, images (OCR), and plain text."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".heic", ".heif",
}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}


def extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        logger.error("pypdf not installed. Run: pip install pypdf")
        return ""
    except Exception as e:
        logger.warning("Failed to extract PDF %s: %s", path, e)
        return ""


def extract_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        logger.error("python-docx not installed. Run: pip install python-docx")
        return ""
    except Exception as e:
        logger.warning("Failed to extract DOCX %s: %s", path, e)
        return ""


def _find_tesseract() -> str | None:
    import shutil
    exe = shutil.which("tesseract")
    if exe:
        return exe
    common = [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ]
    for p in common:
        if p.exists():
            return str(p)
    return None


def extract_image(path: Path) -> str:
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        logger.error("Pillow/pytesseract not installed.")
        return ""

    tess_path = _find_tesseract()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
    else:
        logger.warning("Tesseract not found in PATH or common locations.")
        return ""

    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass

    try:
        img = Image.open(str(path))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        logger.warning("Failed to OCR %s: %s", path, e)
        return ""


def extract_file(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return (extract_pdf(path), "pdf")
    elif suffix in DOCX_EXTENSIONS:
        return (extract_docx(path), "docx")
    elif suffix in IMAGE_EXTENSIONS:
        return (extract_image(path), "image")
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Could not read %s: %s", path, e)
        content = ""
    return (content, "text")
