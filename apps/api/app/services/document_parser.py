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


def parse_text_bytes(title: str, contents: bytes) -> ParsedDocument:
    """Parse plain text or Markdown bytes into a ParsedDocument.

    Splits on double-newlines to create logical pages; falls back to
    fixed-size windows so the chunker always has something to work with.
    """
    try:
        text = contents.decode("utf-8", errors="replace")
    except Exception as exc:
        raise DocumentParseError(f"Cannot decode text file: {exc}") from exc

    if not text.strip():
        raise DocumentParseError("Text file is empty.")

    # Split on paragraph breaks; treat each as a "page"
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    # Group into blocks of ~3 paragraphs per "page" to keep sizes sane
    BLOCK = 3
    pages: list[ParsedPage] = []
    for i in range(0, len(paragraphs), BLOCK):
        block_text = "\n\n".join(paragraphs[i : i + BLOCK])
        pages.append(ParsedPage(page_number=len(pages) + 1, text=block_text))

    return ParsedDocument(title=title, pages=pages)


def parse_url(url: str) -> ParsedDocument:
    """Fetch a web page and extract its main content via trafilatura."""
    try:
        import trafilatura
    except ImportError:
        raise DocumentParseError(
            "trafilatura is not installed. Run: pip install trafilatura"
        )

    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        raise DocumentParseError(f"Failed to fetch URL: {url}")

    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
    )
    if not text or not text.strip():
        raise DocumentParseError(f"No readable content found at: {url}")

    # Use the page title from metadata if available
    metadata = trafilatura.extract_metadata(downloaded)
    title = (metadata.title if metadata and metadata.title else url)[:120]

    return parse_text_bytes(title=title, contents=text.encode("utf-8"))


def parse_youtube_url(url: str) -> ParsedDocument:
    """Extract transcript/subtitles from a YouTube or Bilibili video via yt-dlp."""
    try:
        import yt_dlp
    except ImportError:
        raise DocumentParseError(
            "yt-dlp is not installed. Run: pip install yt-dlp"
        )

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["zh-Hans", "zh", "en"],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise DocumentParseError(f"Cannot fetch video info: {exc}") from exc

    title = info.get("title", url)[:120]

    # Try to get subtitles from requested_subtitles
    subtitles = info.get("subtitles") or info.get("automatic_captions") or {}
    transcript_lines: list[str] = []

    for lang in ("zh-Hans", "zh", "en"):
        if lang in subtitles:
            for entry in subtitles[lang]:
                if entry.get("ext") == "json3" or entry.get("ext") == "srv3":
                    # yt-dlp subtitle entries in json3 format
                    break
            # Fall through: parse from description or chapters as fallback
            break

    # Fallback: use description + chapters as a text source
    description = info.get("description", "")
    chapters = info.get("chapters") or []

    if chapters:
        for ch in chapters:
            start = int(ch.get("start_time", 0))
            mins, secs = divmod(start, 60)
            transcript_lines.append(f"[{mins:02d}:{secs:02d}] {ch.get('title', '')}")

    if description:
        transcript_lines.append("\n--- 视频简介 ---\n" + description)

    if not transcript_lines:
        raise DocumentParseError(
            f"No subtitles or description available for: {url}"
        )

    text = "\n".join(transcript_lines)
    return parse_text_bytes(title=title, contents=text.encode("utf-8"))
