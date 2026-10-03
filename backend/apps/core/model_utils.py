"""Small, shared model helpers with no domain ownership."""

from django.db import models
from django.utils.text import slugify


def unique_slug(instance: models.Model, value: str, field_name: str = "slug") -> str:
    """Return a readable, deterministic unique slug for ``instance``.

    The model's database uniqueness constraint remains the final authority;
    this helper provides a useful default for normal creation flows.
    """

    base_slug = slugify(value)[:220] or "item"
    model_class = type(instance)
    candidate = base_slug
    suffix = 2
    query = model_class._default_manager.all()
    if instance.pk:
        query = query.exclude(pk=instance.pk)
    while query.filter(**{field_name: candidate}).exists():
        suffix_text = f"-{suffix}"
        candidate = f"{base_slug[: 220 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate
