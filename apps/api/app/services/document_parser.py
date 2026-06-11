from dataclasses import dataclass
from pathlib import Path


class DocumentParseError(Exception):
    pass


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    title: str
    pages: list[ParsedPage]


def parse_pdf(path: Path) -> ParsedDocument:
    if path.suffix.lower() != ".pdf":
        raise DocumentParseError(
            f"Only PDF files are supported, got: {path.suffix!r}"
        )
    try:
        contents = path.read_bytes()
    except Exception as exc:
        raise DocumentParseError(f"Cannot read file: {exc}") from exc
    return parse_pdf_bytes(title=path.name, contents=contents)


def parse_pdf_bytes(title: str, contents: bytes) -> ParsedDocument:
    """Parse a PDF from raw bytes — no disk access required."""
    try:
        import fitz
    except ImportError:
        raise DocumentParseError(
            "PyMuPDF is not installed. Run: pip install pymupdf"
        )

    try:
        doc = fitz.open(stream=contents, filetype="pdf")
    except Exception as exc:
        raise DocumentParseError(f"Cannot open PDF (file may be corrupt): {exc}") from exc

    pages: list[ParsedPage] = []
    with doc:
        for index, page in enumerate(doc, start=1):
            pages.append(ParsedPage(page_number=index, text=page.get_text("text").strip()))

    return ParsedDocument(title=title, pages=pages)
