"""Contract ingestion: extract text from PDF, DOCX and TXT. DOCX is read
with the standard library so no extra parser dependency is needed."""
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .config import ALLOWED_UPLOAD_EXTENSIONS


class DocumentError(ValueError):
    pass


def _docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise DocumentError("Invalid or unsupported DOCX file") from exc
    root = ElementTree.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for para in root.iter(f"{{{ns['w']}}}p"):
        runs = [node.text or "" for node in para.iter(f"{{{ns['w']}}}t")]
        text = "".join(runs)
        # Keep numbered headings intact so clause boundaries stay visible.
        paragraphs.append(text)
    return "\n".join(paragraphs)


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise DocumentError("pypdf is not installed") from exc
    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except Exception as exc:  # noqa: BLE001
        raise DocumentError(f"Could not read PDF: {exc}") from exc


def extract_text(filename: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise DocumentError("Unsupported file type; upload PDF, DOCX or TXT")
    if suffix == ".txt":
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")
    elif suffix == ".docx":
        text = _docx_text_from_bytes(raw)
    else:
        text = _pdf_text_from_bytes(raw)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s*Page \d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text.strip():
        raise DocumentError("No readable text found in the document")
    return text.strip()


def _docx_text_from_bytes(raw: bytes) -> str:
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)
    try:
        return _docx_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _pdf_text_from_bytes(raw: bytes) -> str:
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)
    try:
        return _pdf_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
