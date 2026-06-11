from app.services.chunker import chunk_document
from app.services.document_parser import ParsedDocument, ParsedPage


def _make_doc(*page_texts: str) -> ParsedDocument:
    pages = [ParsedPage(page_number=i + 1, text=t) for i, t in enumerate(page_texts)]
    return ParsedDocument(title="test.pdf", pages=pages)


def test_chunk_normal_content():
    doc = _make_doc("Hello world " * 50)
    chunks = chunk_document(document_id="doc1", parsed=doc)
    assert len(chunks) > 0
    assert all(c.document_id == "doc1" for c in chunks)


def test_chunk_empty_page_skipped():
    doc = _make_doc("   ", "\t\n")
    chunks = chunk_document(document_id="doc1", parsed=doc)
    assert chunks == []


def test_chunk_preserves_page_numbers():
    doc = _make_doc("Content on page one.", "Content on page two.")
    chunks = chunk_document(document_id="doc1", parsed=doc)
    pages = {c.page_number for c in chunks}
    assert 1 in pages
    assert 2 in pages


def test_chunk_index_is_sequential():
    doc = _make_doc("word " * 500)
    chunks = chunk_document(document_id="doc1", parsed=doc)
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_chunk_respects_max_chars():
    max_chars = 100
    doc = _make_doc("x " * 200)
    chunks = chunk_document(document_id="doc1", parsed=doc, max_chars=max_chars, overlap=0)
    for chunk in chunks:
        assert len(chunk.content) <= max_chars


def test_chunk_overlap_produces_continuity():
    long_text = "word " * 300
    doc = _make_doc(long_text)
    chunks_no_overlap = chunk_document("d", doc, max_chars=200, overlap=0)
    chunks_with_overlap = chunk_document("d", doc, max_chars=200, overlap=50)
    assert len(chunks_with_overlap) >= len(chunks_no_overlap)
