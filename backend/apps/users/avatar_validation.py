from __future__ import annotations

from django.conf import settings


class AvatarValidationError(ValueError):
    """Raised when an uploaded profile avatar is unsafe or unsupported."""


AVATAR_EXTENSIONS = frozenset({".gif", ".jpeg", ".jpg", ".png", ".webp"})
AVATAR_CONTENT_TYPES = {
    ".gif": frozenset({"image/gif"}),
    ".jpeg": frozenset({"image/jpeg"}),
    ".jpg": frozenset({"image/jpeg"}),
    ".png": frozenset({"image/png"}),
    ".webp": frozenset({"image/webp"}),
}
AVATAR_SIGNATURES = {
    ".gif": (b"GIF87a", b"GIF89a"),
    ".jpeg": (b"\xff\xd8\xff",),
    ".jpg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
}


def _extension(file_name: str) -> str:
    name = file_name.rsplit("/", 1)[-1].casefold()
    return "." + name.rsplit(".", 1)[-1] if "." in name else ""


def _read_head(uploaded_file, length: int = 16) -> bytes:
    position = uploaded_file.tell()
    try:
        uploaded_file.seek(0)
        return uploaded_file.read(length)
    finally:
        uploaded_file.seek(position)


def validate_avatar_file(uploaded_file) -> None:
    extension = _extension(str(getattr(uploaded_file, "name", "")))
    if extension not in AVATAR_EXTENSIONS:
        raise AvatarValidationError("Choose a JPG, PNG, WEBP, or GIF image.")

    if uploaded_file.size > settings.PROFILE_AVATAR_MAX_FILE_SIZE_BYTES:
        max_size_mb = settings.PROFILE_AVATAR_MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise AvatarValidationError(f"Avatar exceeds the maximum allowed size of {max_size_mb:g} MB.")

    content_type = str(getattr(uploaded_file, "content_type", "") or "").split(";", 1)[0].casefold()
    if content_type and content_type not in AVATAR_CONTENT_TYPES[extension]:
        raise AvatarValidationError("The uploaded image content type is not allowed for this extension.")

    head = _read_head(uploaded_file)
    if not any(head.startswith(signature) for signature in AVATAR_SIGNATURES[extension]):
        raise AvatarValidationError("The uploaded image does not match its extension.")
    if extension == ".webp" and head[8:12] != b"WEBP":
        raise AvatarValidationError("The uploaded image does not match its extension.")
