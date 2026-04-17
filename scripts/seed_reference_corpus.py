#!/usr/bin/env python3
"""Seed the retrieval reference corpus from bundled files.

Walks `data/reference-corpus/**/*.{txt,pdf,html,md}`, extracts plain text,
chunks it with a simple sliding window, and writes the result to
`data/reference_chunks.json` (gitignored).

The evidence panel only needs a handful of credible hits, so we cap chunks
per file (5) and total chunks across the corpus (50) to keep seeding fast.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "reference-corpus"
OUT_PATH = ROOT / "data" / "reference_chunks.json"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
MIN_CHUNK_CHARS = 50
MAX_CHUNKS_PER_FILE = 5
MAX_CHUNKS_TOTAL = 50

SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".html", ".htm"}

_WS_RE = re.compile(r"\s+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    stripped = _HTML_TAG_RE.sub(" ", raw)
    return stripped


def _extract(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return _extract_txt(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in (".html", ".htm"):
        return _extract_html(path)
    raise ValueError(f"unsupported suffix: {suffix}")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _chunk(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    step = max(size - overlap, 1)
    for start in range(0, len(text), step):
        piece = text[start : start + size].strip()
        if len(piece) >= MIN_CHUNK_CHARS:
            chunks.append(piece)
        if start + size >= len(text):
            break
    return chunks


def _iter_files(base: Path):
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path


def main() -> int:
    if not CORPUS_DIR.exists():
        print(f"reference-corpus: directory not found: {CORPUS_DIR}", file=sys.stderr)
        return 1

    all_chunks: list[dict] = []

    for path in _iter_files(CORPUS_DIR):
        if len(all_chunks) >= MAX_CHUNKS_TOTAL:
            break
        rel = path.relative_to(ROOT).as_posix()
        try:
            raw = _extract(path)
        except Exception as exc:  # noqa: BLE001 — per spec we warn and continue
            print(f"reference-corpus: SKIP {rel} — {exc}", file=sys.stderr)
            continue

        normalized = _normalize(raw)
        pieces = _chunk(normalized)[:MAX_CHUNKS_PER_FILE]
        for piece in pieces:
            if len(all_chunks) >= MAX_CHUNKS_TOTAL:
                break
            chunk_id = hashlib.sha256(f"{rel}::{piece}".encode("utf-8")).hexdigest()[:12]
            all_chunks.append({"id": chunk_id, "text": piece, "source": rel})

    if not all_chunks:
        print("reference-corpus: no chunks extracted", file=sys.stderr)
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"reference-corpus: wrote {len(all_chunks)} chunks to {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
