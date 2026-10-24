from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.community.models import DiscussionComment, DiscussionCommentLike
from apps.education.models import AcademicLevel, Course, Interest, StudentInterest
from apps.interactions.models import ResourceRating, ResourceUpvote, SavedResource
from apps.users.models import StudentProfile

from .models import PublicationStatus, Resource, ResourceDownload, ResourceView, Video
from .subject_cache import schedule_subjects_cache_invalidation


def _changed_fields(instance, sender, fields):
    if instance._state.adding:
        return True

    update_fields = getattr(instance, "_subjects_cache_update_fields", None)
    if update_fields is not None:
        field_names = set(fields)
        field_names.update(
            field_name[:-3]
            for field_name in fields
            if field_name.endswith("_id")
        )
        return bool(set(update_fields).intersection(field_names))

    old = sender.objects.filter(pk=instance.pk).values(*fields).first()
    if old is None:
        return True
    return any(old[field] != getattr(instance, field) for field in fields)


def _target_is_published(model, object_id):
    if not object_id:
        return False
    return model.objects.filter(pk=object_id, status=PublicationStatus.PUBLISHED).exists()


def _comment_is_relevant(comment):
    return _comment_values_are_relevant(
        comment.status,
        comment.resource_id,
        comment.video_id,
    )


def _comment_values_are_relevant(status, resource_id, video_id):
    target_model, target_id = (
        (Resource, resource_id) if resource_id else (Video, video_id)
    )
    return status == PublicationStatus.PUBLISHED and _target_is_published(target_model, target_id)


def _student_interest_user_id(instance):
    return StudentProfile.objects.filter(pk=instance.student_profile_id).values_list(
        "user_id", flat=True
    ).first()


@receiver(pre_save, sender=Resource)
def resource_before_save(sender, instance, **kwargs):
    instance._subjects_cache_update_fields = kwargs.get("update_fields")
    relevant = _changed_fields(
        instance,
        sender,
        {"status", "subject", "academic_level_id"},
    )
    if instance._state.adding:
        relevant = instance.status == PublicationStatus.PUBLISHED
    elif relevant:
        old = sender.objects.filter(pk=instance.pk).values("status").first()
        relevant = bool(old) and (
            old["status"] == PublicationStatus.PUBLISHED
            or instance.status == PublicationStatus.PUBLISHED
        )
    instance._subjects_cache_relevant_change = relevant


@receiver(post_save, sender=Resource)
def resource_after_save(sender, instance, **kwargs):
    if getattr(instance, "_subjects_cache_relevant_change", False):
        schedule_subjects_cache_invalidation()


@receiver(post_delete, sender=Resource)
def resource_after_delete(sender, instance, **kwargs):
    if instance.status == PublicationStatus.PUBLISHED:
        schedule_subjects_cache_invalidation()


@receiver(pre_save, sender=Video)
def video_before_save(sender, instance, **kwargs):
    instance._subjects_cache_update_fields = kwargs.get("update_fields")
    relevant = _changed_fields(
        instance,
        sender,
        {"status", "subject", "academic_level_id"},
    )
    if instance._state.adding:
        relevant = instance.status == PublicationStatus.PUBLISHED
    elif relevant:
        old = sender.objects.filter(pk=instance.pk).values("status").first()
        relevant = bool(old) and (
            old["status"] == PublicationStatus.PUBLISHED
            or instance.status == PublicationStatus.PUBLISHED
        )
    instance._subjects_cache_relevant_change = relevant


@receiver(post_save, sender=Video)
def video_after_save(sender, instance, **kwargs):
    if getattr(instance, "_subjects_cache_relevant_change", False):
        schedule_subjects_cache_invalidation()


@receiver(post_delete, sender=Video)
def video_after_delete(sender, instance, **kwargs):
    if instance.status == PublicationStatus.PUBLISHED:
        schedule_subjects_cache_invalidation()


def _invalidate_for_published_resource_event(sender, instance, **kwargs):
    target_model = Resource if instance.resource_id else Video
    target_id = instance.resource_id or instance.video_id
    if _target_is_published(target_model, target_id):
        schedule_subjects_cache_invalidation()


# Saves, upvotes, and ratings are lower-volume relationship changes and should
# refresh recommendations immediately. Views and downloads remain append-only
# PostgreSQL history, but do not invalidate Redis on every telemetry write;
# subject recommendations already have a bounded 5-15 minute TTL and can
# safely observe those aggregate changes on the next expiry.
for _event_model in (SavedResource, ResourceUpvote, ResourceRating):
    post_save.connect(
        _invalidate_for_published_resource_event,
        sender=_event_model,
        dispatch_uid=f"subjects-cache-{_event_model._meta.label_lower}-save",
    )
    post_delete.connect(
        _invalidate_for_published_resource_event,
        sender=_event_model,
        dispatch_uid=f"subjects-cache-{_event_model._meta.label_lower}-delete",
    )


@receiver(pre_save, sender=DiscussionComment)
def discussion_comment_before_save(sender, instance, **kwargs):
    instance._subjects_cache_update_fields = kwargs.get("update_fields")
    relevant = _changed_fields(instance, sender, {"status", "resource_id", "video_id"})
    if instance._state.adding:
        instance._subjects_cache_relevant_change = _comment_is_relevant(instance)
        return
    old = sender.objects.filter(pk=instance.pk).values(
        "status", "resource_id", "video_id"
    ).first()
    instance._subjects_cache_relevant_change = bool(
        relevant
        and old
        and (
            _comment_values_are_relevant(
                old["status"], old["resource_id"], old["video_id"]
            )
            or _comment_is_relevant(instance)
        )
    )


@receiver(post_save, sender=DiscussionComment)
def discussion_comment_after_save(sender, instance, **kwargs):
    if getattr(instance, "_subjects_cache_relevant_change", False):
        schedule_subjects_cache_invalidation()


@receiver(post_delete, sender=DiscussionComment)
def discussion_comment_after_delete(sender, instance, **kwargs):
    if _comment_is_relevant(instance):
        schedule_subjects_cache_invalidation()


@receiver(post_save, sender=DiscussionCommentLike)
def discussion_comment_like_after_save(sender, instance, **kwargs):
    comment = DiscussionComment.objects.filter(pk=instance.comment_id).first()
    if comment and _comment_is_relevant(comment):
        schedule_subjects_cache_invalidation()


@receiver(post_delete, sender=DiscussionCommentLike)
def discussion_comment_like_after_delete(sender, instance, **kwargs):
    comment = DiscussionComment.objects.filter(pk=instance.comment_id).first()
    if comment and _comment_is_relevant(comment):
        schedule_subjects_cache_invalidation()


@receiver(pre_save, sender=StudentProfile)
def student_profile_before_save(sender, instance, **kwargs):
    update_fields = kwargs.get("update_fields")
    instance._subjects_cache_update_fields = update_fields
    relevant_fields = {
        "course",
        "course_id",
        "academic_level",
        "academic_level_id",
        "onboarding_completed",
    }
    instance._subjects_cache_relevant_change = _changed_fields(
        instance, sender, relevant_fields
    )


@receiver(post_save, sender=StudentProfile)
def student_profile_after_save(sender, instance, **kwargs):
    if getattr(instance, "_subjects_cache_relevant_change", False):
        schedule_subjects_cache_invalidation(instance.user_id)


@receiver(post_delete, sender=StudentProfile)
def student_profile_after_delete(sender, instance, **kwargs):
    schedule_subjects_cache_invalidation(instance.user_id)


@receiver(post_save, sender=StudentInterest)
def student_interest_after_save(sender, instance, **kwargs):
    user_id = _student_interest_user_id(instance)
    if user_id:
        schedule_subjects_cache_invalidation(user_id)


@receiver(post_delete, sender=StudentInterest)
def student_interest_after_delete(sender, instance, **kwargs):
    user_id = _student_interest_user_id(instance)
    if user_id:
        schedule_subjects_cache_invalidation(user_id)


@receiver(pre_save, sender=Interest)
def interest_before_save(sender, instance, **kwargs):
    instance._subjects_cache_update_fields = kwargs.get("update_fields")
    instance._subjects_cache_relevant_change = _changed_fields(
        instance, sender, {"name", "slug", "is_active"}
    )


@receiver(post_save, sender=Interest)
def interest_after_save(sender, instance, **kwargs):
    if getattr(instance, "_subjects_cache_relevant_change", False):
        schedule_subjects_cache_invalidation()


@receiver(post_delete, sender=Interest)
def interest_after_delete(sender, instance, **kwargs):
    schedule_subjects_cache_invalidation()


@receiver(m2m_changed, sender=Interest.courses.through)
def interest_courses_changed(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        schedule_subjects_cache_invalidation()


@receiver(pre_save, sender=AcademicLevel)
def academic_level_before_save(sender, instance, **kwargs):
    instance._subjects_cache_update_fields = kwargs.get("update_fields")
    instance._subjects_cache_relevant_change = _changed_fields(
        instance, sender, {"course", "course_id"}
    )


@receiver(post_save, sender=AcademicLevel)
def academic_level_after_save(sender, instance, **kwargs):
    if getattr(instance, "_subjects_cache_relevant_change", False):
        schedule_subjects_cache_invalidation()


@receiver(post_delete, sender=AcademicLevel)
def academic_level_after_delete(sender, instance, **kwargs):
    schedule_subjects_cache_invalidation()


@receiver(post_delete, sender=Course)
def course_after_delete(sender, instance, **kwargs):
    schedule_subjects_cache_invalidation()
