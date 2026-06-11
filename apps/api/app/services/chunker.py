import re
from uuid import uuid4

from app.schemas.document import SourceChunk
from app.services.document_parser import ParsedDocument

_MIN_CHUNK_CHARS = 100   # merge short paragraphs below this threshold
_MAX_CHUNK_CHARS = 1200  # hard max for a single chunk
_OVERLAP_CHARS = 150     # char overlap when splitting oversized paragraphs


def _split_paragraphs(text: str) -> list[str]:
    """Split raw page text on paragraph boundaries (2+ newlines).

    Whitespace within each paragraph is collapsed to single spaces so the
    chunk text is clean for embedding.
    """
    raw = re.split(r"\n{2,}", text)
    paras = []
    for p in raw:
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            paras.append(p)
    return paras


def _split_oversized(para: str, max_chars: int, overlap: int) -> list[str]:
    """Split a single oversized paragraph into overlapping sub-chunks."""
    parts = []
    start = 0
    while start < len(para):
        end = min(start + max_chars, len(para))
        parts.append(para[start:end])
        if end == len(para):
            break
        start = max(0, end - overlap)
    return parts


def chunk_document(
    document_id: str,
    parsed: ParsedDocument,
    max_chars: int = _MAX_CHUNK_CHARS,
    overlap: int = _OVERLAP_CHARS,
) -> list[SourceChunk]:
    chunks: list[SourceChunk] = []

    for page in parsed.pages:
        text = page.text.strip()
        if not text:
            continue

        paragraphs = _split_paragraphs(text)
        current: list[str] = []
        current_len = 0

        for para in paragraphs:
            # Paragraph is itself oversized — flush current buffer then split it
            if len(para) > max_chars:
                if current:
                    chunks.append(SourceChunk(
                        id=uuid4().hex,
                        document_id=document_id,
                        chunk_index=len(chunks),
                        content=" ".join(current),
                        page_number=page.page_number,
                    ))
                    current, current_len = [], 0
                for sub in _split_oversized(para, max_chars, overlap):
                    chunks.append(SourceChunk(
                        id=uuid4().hex,
                        document_id=document_id,
                        chunk_index=len(chunks),
                        content=sub,
                        page_number=page.page_number,
                    ))
                continue

            if current_len + len(para) + 1 > max_chars:
                # Flush current buffer
                chunks.append(SourceChunk(
                    id=uuid4().hex,
                    document_id=document_id,
                    chunk_index=len(chunks),
                    content=" ".join(current),
                    page_number=page.page_number,
                ))
                # Keep last paragraph as overlap seed if it fits within overlap budget
                if len(para) <= overlap:
                    current = [para]
                    current_len = len(para)
                else:
                    current = [para]
                    current_len = len(para)
            else:
                current.append(para)
                current_len += len(para) + 1

        # Flush remaining buffer
        if current:
            text_out = " ".join(current)
            # Merge small tail into last chunk only if same page and fits
            if (
                len(text_out) < _MIN_CHUNK_CHARS
                and chunks
                and chunks[-1].page_number == page.page_number
            ):
                prev = chunks[-1]
                merged = prev.content + " " + text_out
                if len(merged) <= max_chars:
                    chunks[-1] = SourceChunk(
                        id=prev.id,
                        document_id=prev.document_id,
                        chunk_index=prev.chunk_index,
                        content=merged,
                        page_number=prev.page_number,
                        section_title=prev.section_title,
                    )
                    continue
            chunks.append(SourceChunk(
                id=uuid4().hex,
                document_id=document_id,
                chunk_index=len(chunks),
                content=text_out,
                page_number=page.page_number,
            ))

    return chunks
