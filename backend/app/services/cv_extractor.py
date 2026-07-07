import io
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader


from app.services.text_normalizer import normalize_cv_text


def extract_text_from_cv(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        text = _extract_pdf(file_bytes)
    elif ext == ".docx":
        text = _extract_docx(file_bytes)
    else:
        raise ValueError("Chỉ hỗ trợ file PDF hoặc DOCX")
    return normalize_cv_text(text)


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    result = "\n".join(parts).strip()
    if not result:
        raise ValueError("Không trích xuất được nội dung từ PDF")
    return result


def _extract_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    result = "\n".join(parts).strip()
    if not result:
        raise ValueError("Không trích xuất được nội dung từ DOCX")
    return result
