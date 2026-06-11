import pytest
import fitz

from app.services.document_parser import DocumentParseError, ParsedDocument, parse_pdf


def test_parse_valid_pdf(valid_pdf_path):
    result = parse_pdf(valid_pdf_path)
    assert isinstance(result, ParsedDocument)
    assert len(result.pages) == 1
    assert "test" in result.pages[0].text.lower()


def test_parse_multi_page_pdf(tmp_path):
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} content")
    path = tmp_path / "multi.pdf"
    path.write_bytes(doc.tobytes())

    result = parse_pdf(path)
    assert len(result.pages) == 3
    assert result.pages[0].page_number == 1
    assert result.pages[2].page_number == 3


def test_parse_blank_page_pdf(tmp_path):
    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "blank.pdf"
    path.write_bytes(doc.tobytes())

    result = parse_pdf(path)
    assert len(result.pages) == 1
    assert result.pages[0].text == ""


def test_parse_non_pdf_raises(tmp_path):
    txt = tmp_path / "file.txt"
    txt.write_text("hello")
    with pytest.raises(DocumentParseError, match="Only PDF"):
        parse_pdf(txt)


def test_parse_corrupt_pdf_raises(tmp_path):
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"this is definitely not a valid pdf file")
    with pytest.raises(DocumentParseError, match="corrupt"):
        parse_pdf(corrupt)


def test_parse_title_is_filename(valid_pdf_path):
    result = parse_pdf(valid_pdf_path)
    assert result.title == valid_pdf_path.name
