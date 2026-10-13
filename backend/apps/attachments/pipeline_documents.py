"""Document stage: DOCX, Markdown and plain text (Section 9.5; Section 12.1; MT-1.12-04).

* **DOCX** — the zip container is opened read-only, its decompressed
  size is capped **before** reading (the MT risk note's zip-bomb guard:
  sum of declared uncompressed sizes vs. a 64 MiB ceiling → clear
  permanent failure, worker intact), then ``word/document.xml`` is
  streamed in document order into markdown-flavoured text: headings →
  ``#``-prefixes, numbered/bulleted paragraphs → ``- `` items, tables →
  pipe rows, everything else → paragraphs. Structure is preserved
  "enough for chunking and summaries" (MT scope) without inventing a
  richer dialect than the inputs carry.
* **Markdown / plain text** — already text: decode UTF-8, normalise
  line endings (CRLF/CR → LF) and drop a leading BOM; **no other
  content transformation** (MT-1.12-04 acceptance: unchanged content).
* **Hostile input** — every parser failure (bad zip, bad CRC, malformed
  XML, undecodable UTF-8) becomes a human-readable
  :class:`PermanentPipelineError`; nothing escapes to kill the worker
  (Section 12.1). Extracted size shares the same text ceiling as PDFs.
"""

from __future__ import annotations

import io
import time
import xml.etree.ElementTree as ET
import zipfile
from typing import Final

from .chunking import ExtractionResult
from .errors import PermanentPipelineError, TransientPipelineError
from .models import TaskAttachment
from .validation import DOCX_MIME, TEXT_MIME_TYPES

#: Zip-bomb ceiling: total *declared* uncompressed bytes across the
#: container (Section 12.1 in-process limit; documented default).
DOCX_MAX_UNCOMPRESSED_BYTES: Final = 64 * 1024 * 1024

#: Output ceiling, same value as the PDF stage (Section 12.1).
MAX_EXTRACTED_CHARS: Final = 5_000_000

#: OOXML wordprocessing namespace (ECMA-376).
_W: Final = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

_HEADING_STYLES: Final[dict[str, int]] = {
    "Title": 1,
    **{f"Heading{level}": level for level in range(1, 7)},
}


def _paragraph_text(paragraph: ET.Element) -> str:
    """Concatenate a ``w:p``'s visible text (runs, tabs, breaks in order)."""
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{_W}t":
            parts.append(node.text or "")
        elif node.tag == f"{_W}tab":
            parts.append("\t")
        elif node.tag in (f"{_W}br", f"{_W}cr"):
            parts.append("\n")
    return "".join(parts)


def _paragraph_block(paragraph: ET.Element) -> str:
    """One ``w:p`` as a markdown block: heading / bullet / plain."""
    props = paragraph.find(f"{_W}pPr")
    prefix = ""
    if props is not None:
        style = props.find(f"{_W}pStyle")
        if style is not None:
            level = _HEADING_STYLES.get(style.get(f"{_W}val", ""))
            if level is not None:
                prefix = f"{'#' * level} "
        if props.find(f"{_W}numPr") is not None and not prefix:
            prefix = "- "
    return f"{prefix}{_paragraph_text(paragraph)}"


def _table_block(table: ET.Element) -> str:
    """One ``w:tbl`` as pipe rows (cells joined in document order)."""
    rows: list[str] = []
    for row in table.findall(f"{_W}tr"):
        cells = []
        for cell in row.findall(f"{_W}tc"):
            text = " ".join(
                block
                for paragraph in cell.findall(f"{_W}p")
                if (block := _paragraph_text(paragraph).strip())
            )
            cells.append(text)
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def docx_to_markdown(xml_bytes: bytes) -> str:
    """Serialize ``word/document.xml`` to markdown-flavoured text."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise PermanentPipelineError(
            "the DOCX document part is malformed XML (permanent content failure)"
        ) from exc
    body = root.find(f"{_W}body")
    if body is None:
        raise PermanentPipelineError("the DOCX document has no body element")

    blocks: list[str] = []
    for child in body:
        if child.tag == f"{_W}p":
            block = _paragraph_block(child)
            if block.strip():  # empty paragraphs become spacing only
                blocks.append(block)
        elif child.tag == f"{_W}tbl":
            block = _table_block(child)
            if block:
                blocks.append(block)
        # w:sectPr and other layout wrappers carry no visible content.
    return "\n\n".join(blocks)


def _read_docx(data: bytes) -> str:
    """Open the container under the size ceiling and extract the body."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise PermanentPipelineError(
            "the stored object is not a readable DOCX zip container"
        ) from exc
    with archive:
        declared = sum(info.file_size for info in archive.infolist())
        if declared > DOCX_MAX_UNCOMPRESSED_BYTES:
            raise PermanentPipelineError(
                f"the DOCX container declares {declared} uncompressed bytes, "
                f"above the {DOCX_MAX_UNCOMPRESSED_BYTES}-byte ceiling "
                "(zip-bomb guard — Section 12.1)"
            )
        try:
            xml_bytes = archive.read("word/document.xml")
        except KeyError as exc:
            raise PermanentPipelineError(
                "the zip container holds no word/document.xml part"
            ) from exc
        except (RuntimeError, zipfile.BadZipFile, OSError) as exc:
            raise PermanentPipelineError(
                f"the DOCX document part could not be read ({type(exc).__name__})"
            ) from exc
    return docx_to_markdown(xml_bytes)


def _decode_text(data: bytes) -> str:
    """UTF-8 decode + line-ending/BOM normalisation (content unchanged)."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PermanentPipelineError(
            "the text file is not valid UTF-8 (permanent content failure)"
        ) from exc
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def process_document(
    attachment: TaskAttachment, data: bytes, *, deadline: float
) -> ExtractionResult:
    """Extract one document attachment into the token-bounded path.

    Persists ``extracted_markdown`` and returns ``ExtractionResult``
    without pages — MT-1.12-05 splits this text into token-bounded
    chunks (Section 9.5 "pages **or** token-bounded chunks").
    """
    if time.monotonic() > deadline:
        raise TransientPipelineError(
            "document parsing exceeded the parse time budget (transient; "
            "retried with backoff — Section 9.9)"
        )
    mime = attachment.mime_type
    if mime == DOCX_MIME:
        text = _read_docx(data)
    elif mime in TEXT_MIME_TYPES or mime == "text/plain":
        text = _decode_text(data)
    else:
        raise PermanentPipelineError(f"unsupported document type {mime!r} for the documents stage")

    if len(text) > MAX_EXTRACTED_CHARS:
        raise PermanentPipelineError(
            f"extracted text exceeds the {MAX_EXTRACTED_CHARS}-character "
            "processing ceiling (Section 12.1 limit)"
        )
    attachment.extracted_markdown = text
    attachment.save(update_fields=["extracted_markdown"])
    return ExtractionResult(text=text)


__all__ = [
    "DOCX_MAX_UNCOMPRESSED_BYTES",
    "MAX_EXTRACTED_CHARS",
    "docx_to_markdown",
    "process_document",
]
