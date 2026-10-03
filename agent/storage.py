from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .audit import DATA_DIR

UPLOAD_DIR = DATA_DIR / "uploads"
BUCKET = os.getenv("GCS_BUCKET", "")
GCS_ENABLED = os.getenv("GET_GCS", "0") == "1" and bool(BUCKET)


@dataclass
class StoredSource:
    id: str
    kind: str
    mime_type: str
    bytes: bytes
    gcs_uri: str | None = None

    @property
    def size_kb(self) -> float:
        return round(len(self.bytes) / 1024, 1)


def classify(filename: str, mime_type: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"} or mime_type.startswith("image/"):
        return "image"
    if ext == ".pdf" or mime_type == "application/pdf":
        return "pdf"
    if ext in {".txt", ".md", ".csv", ".json", ".log"} or mime_type.startswith("text/"):
        return "text"
    return "text"


def save_all(run_id: str, items: list[tuple[str, str, bytes]]) -> list[StoredSource]:
    """items: (filename, mime_type, data). Persists to disk, and to GCS when enabled."""
    outdir = UPLOAD_DIR / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    sources: list[StoredSource] = []
    for filename, mime_type, data in items:
        safe = Path(filename).name or "upload.bin"
        (outdir / safe).write_bytes(data)
        src = StoredSource(
            id=safe, kind=classify(safe, mime_type), mime_type=mime_type, bytes=data
        )
        if GCS_ENABLED:
            src.gcs_uri = _upload_gcs(run_id, src)
        sources.append(src)
    return sources


def _upload_gcs(run_id: str, src: StoredSource) -> str | None:
    try:
        from google.cloud import storage

        client = storage.Client()
        blob = client.bucket(BUCKET).blob(f"{run_id}/{src.id}")
        blob.upload_from_string(src.bytes, content_type=src.mime_type)
        return f"gs://{BUCKET}/{run_id}/{src.id}"
    except Exception as exc:
        print(f"[storage] gcs upload skipped: {exc}")
        return None


def pdf_text(data: bytes) -> str:
    import io

    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        print(f"[storage] pdf text extraction failed: {exc}")
        return ""


def text_of(src: StoredSource) -> str:
    if src.kind == "text":
        return src.bytes.decode("utf-8", errors="replace")
    if src.kind == "pdf":
        return pdf_text(src.bytes)
    return ""