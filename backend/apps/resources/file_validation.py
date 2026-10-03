from __future__ import annotations

import zipfile

from django.conf import settings

from .models import Resource


class ResourceFileValidationError(ValueError):
    """Raised when an uploaded resource file is unsafe or incompatible."""


SUPPORTED_RESOURCE_FILE_EXTENSIONS = frozenset({".pdf", ".ppt", ".pptx", ".doc", ".docx"})

RESOURCE_FILE_EXTENSIONS = {
    Resource.ResourceType.FILE: SUPPORTED_RESOURCE_FILE_EXTENSIONS,
    Resource.ResourceType.PDF: frozenset({".pdf"}),
    Resource.ResourceType.NOTES: SUPPORTED_RESOURCE_FILE_EXTENSIONS,
    Resource.ResourceType.CHEAT_SHEET: frozenset({".pdf", ".doc", ".docx"}),
    Resource.ResourceType.PRESENTATION: frozenset({".pdf", ".ppt", ".pptx"}),
    Resource.ResourceType.ASSIGNMENT: frozenset({".pdf", ".doc", ".docx"}),
    Resource.ResourceType.QUESTION_PAPER: frozenset({".pdf", ".doc", ".docx"}),
    Resource.ResourceType.STUDY_GUIDE: frozenset({".pdf", ".doc", ".docx"}),
    Resource.ResourceType.OTHER: SUPPORTED_RESOURCE_FILE_EXTENSIONS,
}

RESOURCE_FILE_CONTENT_TYPES = {
    ".pdf": frozenset({"application/pdf", "application/octet-stream"}),
    ".doc": frozenset({"application/msword", "application/octet-stream"}),
    ".docx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "application/octet-stream",
        }
    ),
    ".ppt": frozenset({"application/vnd.ms-powerpoint", "application/octet-stream"}),
    ".pptx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/zip",
            "application/octet-stream",
        }
    ),
}

PDF_SIGNATURE = b"%PDF-"
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
EXECUTABLE_SIGNATURES = (b"MZ", b"#!")


def _file_extension(file_name: str) -> str:
    return "." + file_name.rsplit("/", 1)[-1].rsplit(".", 1)[-1].casefold() if "." in file_name else ""


def _read_head(uploaded_file, length: int = 16) -> bytes:
    position = uploaded_file.tell()
    try:
        uploaded_file.seek(0)
        return uploaded_file.read(length)
    finally:
        uploaded_file.seek(position)


def _zip_contains(uploaded_file, required_names: frozenset[str]) -> bool:
    position = uploaded_file.tell()
    try:
        uploaded_file.seek(0)
        with zipfile.ZipFile(uploaded_file) as archive:
            return required_names.issubset(set(archive.namelist()))
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile):
        return False
    finally:
        uploaded_file.seek(position)


def _content_matches_extension(uploaded_file, extension: str) -> bool:
    head = _read_head(uploaded_file)
    if head.startswith(EXECUTABLE_SIGNATURES):
        return False
    if extension == ".pdf":
        return head.startswith(PDF_SIGNATURE)
    if extension in {".doc", ".ppt"}:
        return head.startswith(OLE_SIGNATURE)
    if extension == ".docx":
        return _zip_contains(uploaded_file, frozenset({"[Content_Types].xml", "word/document.xml"}))
    if extension == ".pptx":
        return _zip_contains(uploaded_file, frozenset({"[Content_Types].xml", "ppt/presentation.xml"}))
    return False


def validate_resource_file(uploaded_file, resource_type: str) -> None:
    """Validate a newly uploaded file before Django hands it to storage."""

    extension = _file_extension(str(getattr(uploaded_file, "name", "")))
    allowed_extensions = RESOURCE_FILE_EXTENSIONS.get(resource_type, frozenset())
    if extension not in SUPPORTED_RESOURCE_FILE_EXTENSIONS:
        raise ResourceFileValidationError("Unsupported file type. Choose a PDF, PPT, PPTX, DOC, or DOCX file.")
    if extension not in allowed_extensions:
        label = dict(Resource.ResourceType.choices).get(resource_type, "selected")
        raise ResourceFileValidationError(f"This file type is not allowed for {label} resources.")

    if uploaded_file.size > settings.RESOURCE_MAX_FILE_SIZE_BYTES:
        max_size_mb = settings.RESOURCE_MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise ResourceFileValidationError(f"File exceeds the maximum allowed size of {max_size_mb:g} MB.")

    content_type = str(getattr(uploaded_file, "content_type", "") or "").split(";", 1)[0].casefold()
    if content_type and content_type not in RESOURCE_FILE_CONTENT_TYPES[extension]:
        raise ResourceFileValidationError("The uploaded file content type is not allowed for this extension.")
    if not _content_matches_extension(uploaded_file, extension):
        raise ResourceFileValidationError("The uploaded file content does not match its extension.")
