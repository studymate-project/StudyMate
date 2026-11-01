from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .cache import schedule_education_catalog_invalidation
from .models import AcademicLevel, Course, EducationBackground, Interest


@receiver(post_save, sender=EducationBackground)
@receiver(post_save, sender=Course)
@receiver(post_save, sender=AcademicLevel)
@receiver(post_save, sender=Interest)
def education_catalog_saved(sender, instance, **kwargs):
    schedule_education_catalog_invalidation()


@receiver(post_delete, sender=EducationBackground)
@receiver(post_delete, sender=Course)
@receiver(post_delete, sender=AcademicLevel)
@receiver(post_delete, sender=Interest)
def education_catalog_deleted(sender, instance, **kwargs):
    schedule_education_catalog_invalidation()


@receiver(m2m_changed, sender=Interest.courses.through)
def interest_courses_changed(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        schedule_education_catalog_invalidation()
