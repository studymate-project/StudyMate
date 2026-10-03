from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import uuid4

from cloudinary import utils as cloudinary_utils
from django.conf import settings
from django.core.files.storage import storages

from ..models import Resource

logger = logging.getLogger(__name__)

CLOUDINARY_REFERENCE_PREFIX = "cloudinary://"


class CloudinaryUploadError(Exception):
    """A safe, user-facing error raised when resource storage fails."""


@dataclass(frozen=True)
class CloudinaryUploadResult:
    public_id: str
    secure_url: str
    reference: str


def _extension(file_name: str) -> str:
    if "." not in file_name:
        return ""
    return "." + file_name.rsplit(".", 1)[-1].casefold()


def _resource_segment(resource_type: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "-", str(resource_type).casefold())


def _storage_name(*, resource_type: str, uploader_id: int, extension: str) -> str:
    folder = str(settings.CLOUDINARY_RESOURCE_FOLDER).strip("/")
    return f"{folder}/{_resource_segment(resource_type)}/uploader-{uploader_id}/{uuid4().hex}{extension}"


def _avatar_storage_name(*, uploader_id: int, extension: str) -> str:
    folder = str(settings.CLOUDINARY_AVATAR_FOLDER).strip("/")
    return f"{folder}/user-{uploader_id}/{uuid4().hex}{extension}"


def is_cloudinary_reference(value: str) -> bool:
    return str(value).startswith(CLOUDINARY_REFERENCE_PREFIX)


def _public_id_from_reference(reference: str) -> str:
    return str(reference)[len(CLOUDINARY_REFERENCE_PREFIX) :]


def cloudinary_reference_url(reference: str) -> str | None:
    """Resolve a stored Cloudinary reference without exposing credentials."""

    if not is_cloudinary_reference(reference) or not settings.CLOUDINARY_CONFIGURED:
        return None
    try:
        public_id = _public_id_from_reference(reference)
        if public_id.casefold().endswith(".pdf"):
            return cloudinary_utils.private_download_url(
                public_id,
                "",
                resource_type="raw",
                type="upload",
                attachment=False,
            )
        return storages["cloudinary_media"].url(public_id)
    except Exception:
        logger.exception("Unable to resolve a Cloudinary resource URL")
        return None


def upload_resource_file(*, validated_file, resource_type: str, uploader_id: int) -> CloudinaryUploadResult:
    """Upload an already-validated resource file through the configured storage alias."""

    if not settings.CLOUDINARY_CONFIGURED:
        raise CloudinaryUploadError("Cloudinary resource storage is not configured.")
    if not isinstance(uploader_id, int) or uploader_id <= 0:
        raise CloudinaryUploadError("A valid resource owner is required for file storage.")

    storage_name = _storage_name(
        resource_type=resource_type,
        uploader_id=uploader_id,
        extension=_extension(str(getattr(validated_file, "name", ""))),
    )
    return _upload_to_cloudinary_storage(
        validated_file=validated_file,
        storage_name=storage_name,
        reference_max_length=Resource._meta.get_field("file").max_length or 100,
        failure_message="Resource file storage is temporarily unavailable.",
    )


def upload_profile_avatar(*, validated_file, uploader_id: int) -> CloudinaryUploadResult:
    """Upload an already-validated profile image through the media storage alias."""

    if not settings.CLOUDINARY_CONFIGURED:
        raise CloudinaryUploadError("Cloudinary avatar storage is not configured.")
    if not isinstance(uploader_id, int) or uploader_id <= 0:
        raise CloudinaryUploadError("A valid profile owner is required for avatar storage.")

    from apps.users.models import StudentProfile

    storage_name = _avatar_storage_name(
        uploader_id=uploader_id,
        extension=_extension(str(getattr(validated_file, "name", ""))),
    )
    return _upload_to_cloudinary_storage(
        validated_file=validated_file,
        storage_name=storage_name,
        reference_max_length=StudentProfile._meta.get_field("avatar_reference").max_length,
        failure_message="Profile avatar storage is temporarily unavailable.",
        storage_alias="cloudinary_images",
    )


def _upload_to_cloudinary_storage(
    *,
    validated_file,
    storage_name: str,
    reference_max_length: int,
    failure_message: str,
    storage_alias: str = "cloudinary_media",
) -> CloudinaryUploadResult:
    uploaded_public_id = None
    try:
        storage = storages[storage_alias]
        uploaded_public_id = str(storage.save(storage_name, validated_file))
        if not uploaded_public_id:
            raise RuntimeError("Cloudinary did not return a public identifier.")

        reference = f"{CLOUDINARY_REFERENCE_PREFIX}{uploaded_public_id}"
        if len(reference) > reference_max_length:
            raise RuntimeError("Cloudinary reference exceeds its profile field limit.")
        secure_url = storage.url(uploaded_public_id)
        if not secure_url:
            raise RuntimeError("Cloudinary did not return a secure resource URL.")
        return CloudinaryUploadResult(
            public_id=uploaded_public_id,
            secure_url=secure_url,
            reference=reference,
        )
    except CloudinaryUploadError:
        raise
    except Exception as error:
        if uploaded_public_id:
            _delete_uploaded_file(uploaded_public_id, storage_alias=storage_alias)
        logger.exception("Cloudinary media upload failed")
        raise CloudinaryUploadError(failure_message) from error


def _delete_uploaded_file(public_id: str, *, storage_alias: str = "cloudinary_media") -> None:
    try:
        storages[storage_alias].delete(public_id)
    except Exception:
        logger.exception("Unable to clean up an incomplete Cloudinary resource upload")


def discard_cloudinary_reference(reference: str | None, *, excluding_resource_id: int | None = None) -> None:
    """Delete an owned Cloudinary reference only when no Resource still uses it."""

    if not reference or not is_cloudinary_reference(reference):
        return

    try:
        references = Resource.objects.filter(file=reference)
        if excluding_resource_id is not None:
            references = references.exclude(pk=excluding_resource_id)
        if references.exists():
            return
    except Exception:
        logger.exception("Unable to verify Cloudinary resource reference ownership")
        return
    _delete_uploaded_file(_public_id_from_reference(reference))


def discard_cloudinary_avatar_reference(reference: str | None, *, excluding_profile_id: int | None = None) -> None:
    """Delete an avatar reference only when no profile still uses it."""

    if not reference or not is_cloudinary_reference(reference):
        return

    try:
        from apps.users.models import StudentProfile

        references = StudentProfile.objects.filter(avatar_reference=reference)
        if excluding_profile_id is not None:
            references = references.exclude(pk=excluding_profile_id)
        if references.exists():
            return
    except Exception:
        logger.exception("Unable to verify Cloudinary avatar reference ownership")
        return
    _delete_uploaded_file(_public_id_from_reference(reference), storage_alias="cloudinary_images")


def discard_uploaded_resource(upload_result: CloudinaryUploadResult | None) -> None:
    """Remove a cloud upload if its database transaction cannot be committed."""

    if upload_result is not None:
        discard_cloudinary_reference(upload_result.reference)


def discard_uploaded_avatar(upload_result: CloudinaryUploadResult | None) -> None:
    """Remove an avatar upload if its database transaction cannot be committed."""

    if upload_result is not None:
        discard_cloudinary_avatar_reference(upload_result.reference)
