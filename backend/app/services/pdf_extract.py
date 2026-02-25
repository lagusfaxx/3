from __future__ import annotations
import pdfplumber
from typing import Tuple

def extract_text_from_pdf_bytes(pdf_bytes: bytes, max_pages: int = 30) -> Tuple[str, int]:
    """Extract text from PDF bytes. Returns (text, chars)."""
    text_parts = []
    with pdfplumber.open(io=pdf_bytes) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages]):
            t = page.extract_text() or ""
            t = t.strip()
            if t:
                text_parts.append(f"\n\n--- PAGE {i+1} ---\n{t}")
    full = "\n".join(text_parts).strip()
    return full, len(full)
