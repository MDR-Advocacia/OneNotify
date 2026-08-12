import hashlib
import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any


DOCUMENT_SCHEMA_VERSION = "onenotify.documents.v1"
DEFAULT_MAX_TEXT_CHARS = int(os.getenv("ONENOTIFY_PDF_MAX_TEXT_CHARS", "200000"))
MIN_PAGE_TEXT_CHARS = int(os.getenv("ONENOTIFY_PDF_MIN_PAGE_TEXT_CHARS", "25"))
MIN_DOCUMENT_TEXT_CHARS = int(os.getenv("ONENOTIFY_PDF_MIN_DOCUMENT_TEXT_CHARS", "80"))


def safe_json_loads(value: Any, fallback: Any = None) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _relative_path(path: Path, base_dir: Path | None) -> str | None:
    if base_dir is None:
        return None
    try:
        return str(path.resolve().relative_to(base_dir.resolve()))
    except (OSError, ValueError):
        return None


def _resolve_document_path(raw_path: Any, base_dir: Path | None) -> Path | None:
    if not raw_path:
        return None

    raw = str(raw_path)
    if base_dir is not None:
        normalized = raw.replace("/", "\\")
        windows_prefix = "C:\\OneNotify\\documentos"
        if normalized.lower().startswith(windows_prefix.lower()):
            relative = normalized[len(windows_prefix):].lstrip("\\")
            return base_dir / Path(*relative.split("\\"))

        if raw.startswith("documentos\\") or raw.startswith("documentos/"):
            relative = raw.split("\\", 1)[-1] if "\\" in raw else raw.split("/", 1)[-1]
            return base_dir / Path(*relative.replace("/", "\\").split("\\"))

    return Path(raw)


def _image_count_for_page(page: Any) -> int:
    try:
        return len(page.images)
    except Exception:
        pass

    try:
        resources = page.get("/Resources") or {}
        xobjects = resources.get("/XObject") or {}
        count = 0
        for obj in xobjects.values():
            resolved = obj.get_object()
            if resolved.get("/Subtype") == "/Image":
                count += 1
        return count
    except Exception:
        return 0


def _classify_pdf_extraction(
    page_count: int,
    char_count: int,
    text_pages: int,
    image_pages: int,
) -> tuple[str, bool]:
    if page_count == 0:
        return "empty_pdf", False
    if char_count < MIN_DOCUMENT_TEXT_CHARS and image_pages > 0:
        return "image_only_or_scanned", True
    if char_count < MIN_DOCUMENT_TEXT_CHARS:
        return "no_text_detected", True
    if text_pages < page_count and image_pages > 0:
        return "mixed_text_and_images", True
    return "text_extractable", False


def _extract_pdf_text(path: Path, max_text_chars: int) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        return {
            "status": "dependency_missing",
            "error": f"pypdf indisponivel: {exc}",
            "pages": [],
            "page_count": None,
            "char_count": 0,
            "classification": "dependency_missing",
            "ocr_required": False,
            "text_pages": 0,
            "image_pages": 0,
            "image_count": 0,
            "truncated": False,
        }

    pages: list[dict[str, Any]] = []
    total_chars = 0
    text_pages = 0
    image_pages = 0
    total_images = 0
    truncated = False

    try:
        reader = PdfReader(str(path))
        for index, page in enumerate(reader.pages, start=1):
            if total_chars >= max_text_chars:
                truncated = True
                break
            text = page.extract_text() or ""
            remaining = max_text_chars - total_chars
            if len(text) > remaining:
                text = text[:remaining]
                truncated = True
            total_chars += len(text)
            image_count = _image_count_for_page(page)
            total_images += image_count
            if len(text.strip()) >= MIN_PAGE_TEXT_CHARS:
                text_pages += 1
            if image_count > 0:
                image_pages += 1
            pages.append({
                "page": index,
                "text": text,
                "char_count": len(text),
                "image_count": image_count,
            })

        classification, ocr_required = _classify_pdf_extraction(
            len(reader.pages),
            total_chars,
            text_pages,
            image_pages,
        )

        return {
            "status": "ok" if classification in {"text_extractable", "mixed_text_and_images"} else classification,
            "error": None,
            "pages": pages,
            "page_count": len(reader.pages),
            "char_count": total_chars,
            "classification": classification,
            "ocr_required": ocr_required,
            "text_pages": text_pages,
            "image_pages": image_pages,
            "image_count": total_images,
            "truncated": truncated,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "pages": pages,
            "page_count": len(pages) or None,
            "char_count": total_chars,
            "classification": "error",
            "ocr_required": False,
            "text_pages": text_pages,
            "image_pages": image_pages,
            "image_count": total_images,
            "truncated": truncated,
        }


def document_to_json(document: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, Any]:
    raw_path = document.get("caminho") or document.get("path") or document.get("arquivo")
    base_path = Path(base_dir) if base_dir else None
    path = _resolve_document_path(raw_path, base_path)
    exists = bool(path and path.exists())
    suffix = path.suffix.lower() if path else ""

    payload: dict[str, Any] = {
        "nome": document.get("nome") or (path.name if path else None),
        "original_path": str(raw_path) if raw_path else None,
        "resolved_path": str(path) if path else None,
        "relative_path": _relative_path(path, base_path) if path else None,
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": _sha256(path) if exists else None,
        "mime_type": mimetypes.guess_type(str(path))[0] if path else None,
        "source": "onenotify-rpa",
        "extraction": {
            "status": "not_extracted",
            "error": None,
            "pages": [],
            "page_count": None,
            "char_count": 0,
            "classification": "not_extracted",
            "ocr_required": False,
            "text_pages": 0,
            "image_pages": 0,
            "image_count": 0,
            "truncated": False,
        },
    }

    if exists and suffix == ".pdf":
        payload["extraction"] = _extract_pdf_text(path, DEFAULT_MAX_TEXT_CHARS)
    elif exists and suffix in {".txt", ".text"}:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            truncated = len(text) > DEFAULT_MAX_TEXT_CHARS
            text = text[:DEFAULT_MAX_TEXT_CHARS]
            payload["extraction"] = {
                "status": "ok",
                "error": None,
                "pages": [{"page": 1, "text": text, "char_count": len(text)}],
                "page_count": 1,
                "char_count": len(text),
                "classification": "text_extractable",
                "ocr_required": False,
                "text_pages": 1 if text.strip() else 0,
                "image_pages": 0,
                "image_count": 0,
                "truncated": truncated,
            }
        except OSError as exc:
            payload["extraction"] = {
                "status": "error",
                "error": str(exc),
                "pages": [],
                "page_count": None,
                "char_count": 0,
                "classification": "error",
                "ocr_required": False,
                "text_pages": 0,
                "image_pages": 0,
                "image_count": 0,
                "truncated": False,
            }
    elif not exists:
        payload["extraction"]["status"] = "missing_file"
        payload["extraction"]["classification"] = "missing_file"

    return payload


def build_documents_json(
    documents: list[dict[str, Any]] | str | None,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    parsed = safe_json_loads(documents, fallback=[])
    if not isinstance(parsed, list):
        parsed = []

    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "items": [document_to_json(doc, base_dir=base_dir) for doc in parsed if isinstance(doc, dict)],
    }
