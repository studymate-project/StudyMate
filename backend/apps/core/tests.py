from datetime import timedelta
from typing import ClassVar
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.community.models import Answer, Question
from apps.community.serializers import AnswerSerializer, QuestionSerializer
from apps.core.pagination import StudyMatePagination
from apps.education.models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest
from apps.education.serializers import AcademicLevelSerializer, CourseSerializer, EducationBackgroundSerializer, InterestSerializer, StudentInterestSerializer
from apps.interactions.models import AnswerUpvote, QuestionUpvote, ResourceUpvote, SavedResource, UserFollow
from apps.interactions.serializers import AnswerUpvoteSerializer, QuestionUpvoteSerializer, ResourceUpvoteSerializer, SavedResourceSerializer
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.resources.models import PublicationStatus, Resource, ResourceDownload, ResourceView, Tag, Video
from apps.resources.serializers import ResourceSerializer, VideoSerializer
from apps.resources.youtube import normalize_youtube_video_id
from apps.users.models import StudentProfile
from apps.users.serializers import RegistrationSerializer, StudentProfileSerializer


class YouTubeVideoIDTests(TestCase):
    def test_normalizes_supported_youtube_url_formats(self):
        video_id = "dQw4w9WgXcQ"
        values = (
            video_id,
            f"https://www.youtube.com/watch?v={video_id}",
            f"https://youtu.be/{video_id}",
            f"https://www.youtube.com/embed/{video_id}",
        )

        for value in values:
            with self.subTest(value=value):
                self.assertEqual(normalize_youtube_video_id(value), video_id)

    def test_rejects_non_youtube_urls_and_malformed_video_ids(self):
        invalid_values = (
            "https://vimeo.com/123456789",
            "https://www.youtube.com/watch?v=not-a-valid-id",
            "https://www.youtube.com/embed/dQw4w9WgXcQ/untrusted",
            '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>',
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    normalize_youtube_video_id(value)

    def test_video_serializer_stores_the_normalized_id(self):
        serializer = VideoSerializer(
            data={
                "title": "Normalized video",
                "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
                "subject": "Physics",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["youtube_url"], "dQw4w9WgXcQ")

    def test_video_model_normalizes_before_storage(self):
        user = User.objects.create_user(username="video-owner", password="not-used-in-test")
        video = Video.objects.create(
            title="Stored video",
            uploader=user,
            youtube_video_id="https://www.youtube.com/embed/dQw4w9WgXcQ",
            subject="Physics",
        )

        self.assertEqual(video.youtube_video_id, "dQw4w9WgXcQ")

    def test_database_rejects_non_normalized_video_ids(self):
        user = User.objects.create_user(username="video-constraint-owner", password="not-used-in-test")
        video = Video.objects.create(
            title="Constrained video",
            uploader=user,
            youtube_video_id="dQw4w9WgXcQ",
            subject="Physics",
        )

        with self.assertRaises(IntegrityError):
            Video.objects.filter(pk=video.pk).update(youtube_video_id="abc!efghijk")


class VideoAPIYouTubeURLTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="video-api-owner", password="not-used-in-test")
        cls.other_user = User.objects.create_user(username="video-api-peer", password="not-used-in-test")

    def setUp(self) -> None:
        self.client = APIClient()

    def create_video(self, youtube_url: str, expected_video_id: str):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/videos/",
            {
                "title": "Submitted video",
                "subject": "Physics",
                "youtube_url": youtube_url,
                "youtube_video_id": "A1b2C3d4E5F",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["youtube_video_id"], expected_video_id)
        self.assertNotIn("youtube_url", response.data)
        self.assertEqual(Video.objects.get(pk=response.data["id"]).youtube_video_id, expected_video_id)

    def test_accepts_watch_url(self):
        self.create_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ")

    def test_accepts_short_url(self):
        self.create_video("https://youtu.be/3JZ_D3ELwOQ", "3JZ_D3ELwOQ")

    def test_accepts_embed_url(self):
        self.create_video("https://www.youtube.com/embed/9bZkp7q19f0", "9bZkp7q19f0")

    def test_rejects_non_youtube_url(self):
        self.client.force_authenticate(user=self.user)
        invalid_urls = (
            "https://vimeo.com/123456789",
            '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>',
            "https://www.youtube.com/watch",
            "https://www.youtube.com/watch?v=not-a-valid-id",
            "https://youtu.be/too-short",
            "https://www.youtube.com/embed/dQw4w9WgXcQ/untrusted",
        )

        for youtube_url in invalid_urls:
            with self.subTest(youtube_url=youtube_url):
                response = self.client.post(
                    "/api/videos/",
                    {"title": "Invalid video", "subject": "Physics", "youtube_url": youtube_url},
                    format="json",
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn("youtube_url", response.data)

    def test_rejects_missing_required_video_data(self):
        self.client.force_authenticate(user=self.user)
        invalid_payloads = (
            (
                {"title": "Missing URL", "subject": "Physics"},
                "youtube_url",
            ),
            (
                {"subject": "Physics", "youtube_url": "https://youtu.be/dQw4w9WgXcQ"},
                "title",
            ),
            (
                {"title": "Missing subject", "youtube_url": "https://youtu.be/dQw4w9WgXcQ"},
                "subject",
            ),
        )

        for payload, field in invalid_payloads:
            with self.subTest(field=field):
                response = self.client.post("/api/videos/", payload, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_missing_video_detail_returns_not_found(self):
        response = self.client.get("/api/videos/does-not-exist/")

        self.assertEqual(response.status_code, 404)

    def test_rejects_legacy_external_video_url_field(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/videos/",
            {
                "title": "Legacy URL video",
                "subject": "Physics",
                "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
                "original_url": "https://vimeo.com/123456789",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("original_url", response.data)

    def test_rejects_unauthenticated_video_submission(self):
        response = self.client.post(
            "/api/videos/",
            {
                "title": "Unauthenticated video",
                "subject": "Physics",
                "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_existing_resource_ownership_rule_is_preserved(self):
        resource = Resource.objects.create(
            title="Owner notes",
            uploader=self.user,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(f"/api/resources/{resource.pk}/", {"title": "Changed"}, format="json")

        self.assertEqual(response.status_code, 403)
        resource.refresh_from_db()
        self.assertEqual(resource.title, "Owner notes")

    def test_non_video_resources_still_create_normally(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/resources/",
            {"title": "Notes", "subject": "Physics", "resource_type": Resource.ResourceType.NOTES},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["resource_type"], Resource.ResourceType.NOTES)


class DomainModelTests(TestCase):
    user: ClassVar[User]
    other_user: ClassVar[User]
    background: ClassVar[EducationBackground]
    other_background: ClassVar[EducationBackground]
    course: ClassVar[Course]
    other_course: ClassVar[Course]
    level: ClassVar[AcademicLevel]
    other_level: ClassVar[AcademicLevel]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="student", password="not-used-in-test")
        cls.other_user = User.objects.create_user(username="peer", password="not-used-in-test")
        cls.background = EducationBackground.objects.create(name="Engineering", slug="domain-engineering")
        cls.other_background, _ = EducationBackground.objects.get_or_create(
            slug="school", defaults={"name": "School"}
        )
        cls.course = Course.objects.create(education_background=cls.background, name="B.Tech", slug="btech")
        cls.other_course = Course.objects.create(education_background=cls.other_background, name="Class 12", slug="class-12")
        cls.level = AcademicLevel.objects.create(
            course=cls.course, name="Semester 1", slug="semester-1", level_type=AcademicLevel.LevelType.SEMESTER, order=1
        )
        cls.other_level = AcademicLevel.objects.create(
            course=cls.other_course, name="Class 12", slug="class-12", level_type=AcademicLevel.LevelType.CLASS, order=12
        )

    def create_profile(self) -> StudentProfile:
        return StudentProfile.objects.create(
            user=self.user, education_background=self.background, course=self.course, academic_level=self.level
        )

    def create_resource(self) -> Resource:
        return Resource.objects.create(
            title="Study notes", uploader=self.user, subject="Physics", academic_level=self.level,
            resource_type=Resource.ResourceType.NOTES,
        )

    def test_student_profile_is_one_to_one_with_user(self):
        self.create_profile()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentProfile.objects.create(user=self.user)

    def test_student_interest_cannot_be_duplicated(self):
        profile = self.create_profile()
        interest = Interest.objects.create(name="Thermodynamics", slug="thermodynamics")
        StudentInterest.objects.create(student_profile=profile, interest=interest)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentInterest.objects.create(student_profile=profile, interest=interest)

    def test_profile_rejects_inconsistent_education_selection(self):
        profile = StudentProfile(user=self.user, education_background=self.background, course=self.other_course, academic_level=self.level)
        with self.assertRaises(ValidationError):
            profile.full_clean()
        profile = StudentProfile(user=self.user, education_background=self.background, course=self.course, academic_level=self.other_level)
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_profiles_support_semester_year_and_class_levels(self):
        mba_background = EducationBackground.objects.create(name="Management", slug="management")
        mba_course = Course.objects.create(education_background=mba_background, name="MBA", slug="mba")
        mba_level = AcademicLevel.objects.create(
            course=mba_course, name="2nd Year", slug="year-2", level_type=AcademicLevel.LevelType.YEAR, order=2
        )
        school_course = Course.objects.create(education_background=self.other_background, name="School", slug="school")
        school_level = AcademicLevel.objects.create(
            course=school_course, name="Class 10", slug="class-10", level_type=AcademicLevel.LevelType.CLASS, order=10
        )
        school_user = User.objects.create_user(username="school-student", password="not-used-in-test")

        btech_profile = StudentProfile.objects.create(
            user=self.user, education_background=self.background, course=self.course, academic_level=self.level
        )
        mba_profile = StudentProfile.objects.create(
            user=self.other_user, education_background=mba_background, course=mba_course, academic_level=mba_level
        )
        school_profile = StudentProfile.objects.create(
            user=school_user,
            education_background=self.other_background,
            course=school_course,
            academic_level=school_level,
        )

        self.assertEqual(btech_profile.academic_level.level_type, AcademicLevel.LevelType.SEMESTER)
        self.assertEqual(mba_profile.academic_level.level_type, AcademicLevel.LevelType.YEAR)
        self.assertEqual(school_profile.academic_level.level_type, AcademicLevel.LevelType.CLASS)
        self.assertEqual(mba_profile.course.education_background, mba_profile.education_background)
        self.assertEqual(school_profile.user, school_user)

    def test_profile_defaults_and_nonnegative_contribution_points_constraint(self):
        profile = StudentProfile.objects.create(user=self.user)
        self.assertFalse(profile.onboarding_completed)
        self.assertEqual(profile.contribution_points, 0)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentProfile.objects.create(user=self.other_user, contribution_points=-1)

    def test_resource_relationships_and_unique_slug_generation(self):
        resource = self.create_resource()
        duplicate = Resource.objects.create(
            title="Study notes", uploader=self.other_user, subject="Physics", academic_level=self.level,
            resource_type=Resource.ResourceType.NOTES,
        )
        self.assertEqual(resource.uploader, self.user)
        self.assertEqual(resource.academic_level, self.level)
        self.assertEqual(resource.slug, "study-notes")
        self.assertEqual(duplicate.slug, "study-notes-2")

    def test_resource_supports_cheat_sheet_type(self):
        resource = Resource.objects.create(
            title="Formula sheet",
            uploader=self.user,
            subject="Physics",
            resource_type=Resource.ResourceType.CHEAT_SHEET,
        )

        self.assertEqual(resource.resource_type, Resource.ResourceType.CHEAT_SHEET)

    def test_resource_tag_relationship_cannot_be_duplicated(self):
        resource = self.create_resource()
        tag = Tag.objects.create(name="Mechanics", slug="mechanics")
        resource.tags.add(tag)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Resource.tags.through.objects.create(resource=resource, tag=tag)

    def test_education_catalog_relationships(self):
        self.assertEqual(self.course.education_background, self.background)
        self.assertEqual(self.level.course, self.course)
        self.assertEqual(list(self.background.courses.all()), [self.course])
        self.assertEqual(list(self.course.academic_levels.all()), [self.level])

    def test_video_tags_and_resource_events_are_relational(self):
        resource = self.create_resource()
        tag = Tag.objects.create(name="Physics", slug="physics")
        resource.tags.add(tag)
        video = Video.objects.create(
            title="Newton's laws",
            uploader=self.user,
            youtube_video_id="dQw4w9WgXcQ",
            subject="Physics",
        )
        video.tags.add(tag)
        view = ResourceView.objects.create(resource=resource, user=self.other_user)
        download = ResourceDownload.objects.create(resource=resource, user=self.other_user)

        self.assertEqual(list(tag.resources.all()), [resource])
        self.assertEqual(list(tag.videos.all()), [video])
        self.assertEqual(view.resource, resource)
        self.assertEqual(download.user, self.other_user)
        self.assertEqual(video.slug, "newtons-laws")

    def test_video_ownership_and_unique_slug_generation(self):
        video = Video.objects.create(
            title="Calculus basics", uploader=self.user, youtube_video_id="A1b2C3d4E5F", subject="Mathematics"
        )
        duplicate = Video.objects.create(
            title="Calculus basics", uploader=self.other_user, youtube_video_id="G6h7I8j9K0L", subject="Mathematics"
        )

        self.assertEqual(video.uploader, self.user)
        self.assertEqual(video.slug, "calculus-basics")
        self.assertEqual(duplicate.slug, "calculus-basics-2")

    def test_saved_resource_is_unique_per_user_and_resource(self):
        resource = self.create_resource()
        SavedResource.objects.create(user=self.user, resource=resource)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SavedResource.objects.create(user=self.user, resource=resource)

    def test_different_users_can_save_the_same_resource(self):
        resource = self.create_resource()
        first_save = SavedResource.objects.create(user=self.user, resource=resource)
        second_save = SavedResource.objects.create(user=self.other_user, resource=resource)

        self.assertNotEqual(first_save.pk, second_save.pk)
        self.assertEqual(SavedResource.objects.filter(resource=resource).count(), 2)

    def test_interaction_uniqueness_constraints(self):
        resource = self.create_resource()
        question = Question.objects.create(title="A question", body="Question body", author=self.user, subject="Physics")
        answer = Answer.objects.create(question=question, author=self.other_user, body="Answer body")

        ResourceUpvote.objects.create(user=self.user, resource=resource)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ResourceUpvote.objects.create(user=self.user, resource=resource)

        QuestionUpvote.objects.create(user=self.user, question=question)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuestionUpvote.objects.create(user=self.user, question=question)

        AnswerUpvote.objects.create(user=self.user, answer=answer)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AnswerUpvote.objects.create(user=self.user, answer=answer)

    def test_question_answer_relationship(self):
        question = Question.objects.create(
            title="A question", body="Question body", author=self.user, subject="Physics", academic_level=self.level
        )
        answer = Answer.objects.create(question=question, author=self.other_user, body="Answer body")
        self.assertEqual(list(question.answers.all()), [answer])
        self.assertEqual(question.academic_level, self.level)
        self.assertEqual(answer.author, self.other_user)

    def test_question_slug_is_unique_and_generated(self):
        question = Question.objects.create(title="Exam preparation", body="Question body", author=self.user, subject="Physics")
        duplicate = Question.objects.create(
            title="Exam preparation", body="Another question body", author=self.other_user, subject="Physics"
        )

        self.assertEqual(question.slug, "exam-preparation")
        self.assertEqual(duplicate.slug, "exam-preparation-2")

    def test_timestamps_are_populated_and_updated(self):
        resource = self.create_resource()
        self.assertIsNotNone(resource.created_at)
        self.assertIsNotNone(resource.updated_at)
        self.assertGreaterEqual(resource.updated_at, resource.created_at)

        initial_updated_at = resource.updated_at
        resource.title = "Updated study notes"
        resource.save()
        resource.refresh_from_db()

        self.assertGreater(resource.updated_at, initial_updated_at)

    def test_question_deletion_cascades_to_answers_and_answer_upvotes(self):
        question = Question.objects.create(title="A question", body="Question body", author=self.user, subject="Physics")
        answer = Answer.objects.create(question=question, author=self.other_user, body="Answer body")
        upvote = AnswerUpvote.objects.create(user=self.user, answer=answer)

        question.delete()

        self.assertFalse(Answer.objects.filter(pk=answer.pk).exists())
        self.assertFalse(AnswerUpvote.objects.filter(pk=upvote.pk).exists())

    def test_resource_deletion_cascades_to_interactions(self):
        resource = self.create_resource()
        saved_resource = SavedResource.objects.create(user=self.other_user, resource=resource)
        upvote = ResourceUpvote.objects.create(user=self.other_user, resource=resource)

        resource.delete()

        self.assertFalse(SavedResource.objects.filter(pk=saved_resource.pk).exists())
        self.assertFalse(ResourceUpvote.objects.filter(pk=upvote.pk).exists())

    def test_owned_content_prevents_user_deletion(self):
        self.create_resource()

        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_profile_is_deleted_with_its_user_and_unused_background_is_nullable(self):
        profile = self.create_profile()
        profile_user = profile.user
        profile_user.delete()

        self.assertFalse(StudentProfile.objects.filter(pk=profile.pk).exists())

        user_without_content = User.objects.create_user(username="background-test", password="not-used-in-test")
        background = EducationBackground.objects.create(name="Arts", slug="arts")
        nullable_profile = StudentProfile.objects.create(user=user_without_content, education_background=background)
        background.delete()
        nullable_profile.refresh_from_db()

        self.assertIsNone(nullable_profile.education_background)

    def test_follow_is_unique_and_cannot_be_self_follow(self):
        UserFollow.objects.create(follower=self.user, following=self.other_user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserFollow.objects.create(follower=self.user, following=self.other_user)
        self_follow = UserFollow(follower=self.user, following=self.user)
        with self.assertRaises(ValidationError):
            self_follow.full_clean()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserFollow.objects.create(follower=self.user, following=self.user)

    def test_notification_has_recipient_and_generic_resource_reference(self):
        resource = self.create_resource()
        notification = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.RESOURCE_UPVOTED,
            content_object=resource,
        )
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.actor, self.other_user)
        self.assertEqual(notification.content_object, resource)
        self.assertFalse(notification.is_read)
        self.assertIsNotNone(notification.created_at)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Notification.objects.create(recipient=self.user, notification_type="unsupported")


class NotificationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.recipient = User.objects.create_user(username="notification-recipient", password="not-used-in-test")
        cls.actor = User.objects.create_user(username="notification-actor", password="not-used-in-test")
        cls.resource = Resource.objects.create(
            title="Notification resource",
            uploader=cls.actor,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
        )

    def test_notification_stores_relationships_payload_and_unread_state(self):
        notification = Notification.objects.create(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.RESOURCE_UPVOTED,
            content_object=self.resource,
            payload={"resource_id": self.resource.pk, "reason": "helpful"},
        )

        self.assertEqual(notification.recipient, self.recipient)
        self.assertEqual(notification.actor, self.actor)
        self.assertEqual(notification.payload, {"resource_id": self.resource.pk, "reason": "helpful"})
        self.assertFalse(notification.is_read)
        self.assertIsNotNone(notification.created_at)
        self.assertIn(notification, self.recipient.notifications.all())
        self.assertIn(notification, self.actor.notifications_created.all())

    def test_notification_supports_nullable_actor_for_system_events(self):
        notification = Notification.objects.create(
            recipient=self.recipient,
            notification_type=Notification.NotificationType.SYSTEM,
            payload={"message": "Maintenance scheduled"},
        )

        self.assertIsNone(notification.actor)
        self.assertEqual(notification.payload["message"], "Maintenance scheduled")

    def test_notification_related_object_uses_generic_reference(self):
        notification = Notification.objects.create(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.RESOURCE_SAVED,
            content_object=self.resource,
        )

        notification.refresh_from_db()
        self.assertEqual(notification.content_object, self.resource)
        self.assertEqual(notification.object_id, self.resource.pk)
        self.assertIsNotNone(notification.content_type_id)

    def test_notification_read_state_can_be_updated(self):
        notification = Notification.objects.create(
            recipient=self.recipient,
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.assertFalse(notification.is_read)

        notification.is_read = True
        notification.save(update_fields=["is_read"])
        notification.refresh_from_db()

        self.assertTrue(notification.is_read)

    def test_notification_payload_rejects_non_json_data(self):
        notification = Notification(
            recipient=self.recipient,
            notification_type=Notification.NotificationType.SYSTEM,
            payload={"invalid": object()},
        )

        with self.assertRaises(ValidationError):
            notification.full_clean()


class APIFoundationTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_api_root_lists_reserved_namespaces(self):
        response = self.client.get("/api/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["service"], "studymate-api")
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["namespaces"]["resources"], "/api/resources/")

    def test_health_endpoint_remains_public(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})

    def test_openapi_schema_endpoint_exposes_api_routes_and_auth_schemes(self):
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.oai.openapi", response["Content-Type"])
        self.assertIn(b"/api/resources/", response.content)
        self.assertIn(b"bearerAuth", response.content)
        self.assertIn(b"jwtCookieAuth", response.content)

    def test_swagger_ui_endpoint_is_available(self):
        response = self.client.get("/api/docs/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        self.assertIn(b"StudyMate API", response.content)

    def test_openapi_documents_filters_permissions_and_validation_responses(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        resource_list = schema["paths"]["/api/resources/"]["get"]
        resource_filters = {parameter["name"] for parameter in resource_list["parameters"]}
        self.assertTrue(
            {"search", "subject", "topic", "resource_type", "academic_level", "difficulty", "tags", "ordering"}
            <= resource_filters
        )

        resource_update = schema["paths"]["/api/resources/{lookup}/"]["patch"]
        self.assertTrue({"400", "401", "403", "404"} <= set(resource_update["responses"]))
        onboarding = schema["paths"]["/api/users/onboarding/"]["post"]
        self.assertTrue({"200", "400", "401"} <= set(onboarding["responses"]))
        notification_read = schema["paths"]["/api/notifications/{id}/read/"]["patch"]
        self.assertTrue({"200", "401", "403", "404"} <= set(notification_read["responses"]))

    def test_openapi_matches_request_response_boundaries_and_auth_flow(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        resource_request = schema["components"]["schemas"]["ResourceRequest"]
        self.assertEqual(set(resource_request["required"]), {"resource_type", "subject", "title"})
        self.assertNotIn("uploader", resource_request["properties"])
        self.assertNotIn("status", resource_request["properties"])

        video_request = schema["components"]["schemas"]["VideoRequest"]
        self.assertIn("youtube_url", video_request["required"])
        self.assertNotIn("youtube_video_id", video_request["properties"])
        self.assertNotIn("youtube_url", schema["components"]["schemas"]["Video"]["properties"])

        protected_create = schema["paths"]["/api/resources/"]["post"]
        public_list = schema["paths"]["/api/resources/"]["get"]
        self.assertNotIn({}, protected_create["security"])
        self.assertIn({}, public_list["security"])

        refresh = schema["paths"]["/api/auth/refresh/"]["post"]
        logout = schema["paths"]["/api/auth/logout/"]["post"]
        self.assertIn("X-CSRFToken", {parameter["name"] for parameter in refresh["parameters"]})
        self.assertIn("X-CSRFToken", {parameter["name"] for parameter in logout["parameters"]})
        self.assertIn("jwtCookieAuth", schema["components"]["securitySchemes"])
        self.assertIn("X-CSRFToken", schema["components"]["securitySchemes"]["jwtCookieAuth"]["description"])

        answer_detail = schema["paths"]["/api/questions/{question_id}/answers/{id}/"]["patch"]
        path_parameters = {parameter["name"]: parameter["schema"]["type"] for parameter in answer_detail["parameters"]}
        self.assertEqual(path_parameters, {"question_id": "integer", "id": "integer"})
        self.assertTrue({"400", "401", "403", "404"} <= set(answer_detail["responses"]))
        answer_list = schema["paths"]["/api/questions/{question_id}/answers/"]["get"]
        self.assertIn("200", answer_list["responses"])
        self.assertIn("404", answer_list["responses"])


class SerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="serializer-user", password="not-used-in-test")
        cls.other_user = User.objects.create_user(username="serializer-peer", password="not-used-in-test")
        cls.background = EducationBackground.objects.create(name="Engineering", slug="serializer-engineering")
        cls.course = Course.objects.create(
            education_background=cls.background, name="B.Tech", slug="serializer-btech"
        )
        cls.level = AcademicLevel.objects.create(
            course=cls.course,
            name="5th Semester",
            slug="serializer-semester-5",
            level_type=AcademicLevel.LevelType.SEMESTER,
            order=5,
        )
        cls.interest = Interest.objects.create(name="Physics", slug="serializer-physics")
        cls.profile = StudentProfile.objects.create(
            user=cls.user,
            education_background=cls.background,
            course=cls.course,
            academic_level=cls.level,
        )
        cls.tag = Tag.objects.create(name="Serializer Tag", slug="serializer-tag")
        cls.resource = Resource.objects.create(
            title="Serializer notes",
            uploader=cls.user,
            subject="Physics",
            academic_level=cls.level,
            resource_type=Resource.ResourceType.NOTES,
        )
        cls.resource.tags.add(cls.tag)
        cls.video = Video.objects.create(
            title="Serializer video",
            uploader=cls.user,
            youtube_video_id="AbCdEfGhIjK",
            subject="Physics",
        )
        cls.question = Question.objects.create(
            title="Serializer question", body="Question body", author=cls.user, subject="Physics"
        )
        cls.answer = Answer.objects.create(question=cls.question, author=cls.other_user, body="Answer body")

    def test_core_serializers_expose_safe_fields(self):
        profile_data = StudentProfileSerializer(self.profile).data
        resource_data = ResourceSerializer(self.resource).data
        video_data = VideoSerializer(self.video).data
        question_data = QuestionSerializer(self.question).data
        answer_data = AnswerSerializer(self.answer).data

        self.assertNotIn("password", profile_data["user"])
        self.assertEqual(resource_data["uploader"]["username"], "serializer-user")
        self.assertEqual(resource_data["tags"][0]["slug"], "serializer-tag")
        self.assertEqual(video_data["youtube_video_id"], "AbCdEfGhIjK")
        self.assertEqual(question_data["author"]["username"], "serializer-user")
        self.assertEqual(answer_data["author"]["username"], "serializer-peer")

    def test_question_and_answer_serializers_expose_relationship_counts(self):
        QuestionUpvote.objects.create(user=self.user, question=self.question)
        AnswerUpvote.objects.create(user=self.other_user, answer=self.answer)

        question_data = QuestionSerializer(self.question).data
        answer_data = AnswerSerializer(self.answer).data

        self.assertEqual(question_data["upvotes"], 1)
        self.assertEqual(question_data["answers"], 1)
        self.assertEqual(answer_data["upvotes"], 1)

    def test_question_and_answer_serializers_ignore_protected_input_fields(self):
        question_serializer = QuestionSerializer(
            data={
                "title": "Client-owned question",
                "body": "Question body",
                "subject": "Physics",
                "author": self.other_user.pk,
                "slug": "client-slug",
                "status": PublicationStatus.ARCHIVED,
                "upvotes": 999,
                "answers": 999,
            }
        )
        answer_serializer = AnswerSerializer(
            data={
                "body": "Client-owned answer",
                "question": self.question.pk,
                "author": self.other_user.pk,
                "is_helpful": True,
                "status": PublicationStatus.ARCHIVED,
                "upvotes": 999,
            }
        )

        self.assertTrue(question_serializer.is_valid(), question_serializer.errors)
        self.assertTrue(answer_serializer.is_valid(), answer_serializer.errors)
        self.assertNotIn("author", question_serializer.validated_data)
        self.assertNotIn("slug", question_serializer.validated_data)
        self.assertNotIn("status", question_serializer.validated_data)
        self.assertNotIn("question", answer_serializer.validated_data)
        self.assertNotIn("author", answer_serializer.validated_data)
        self.assertNotIn("is_helpful", answer_serializer.validated_data)

    def test_question_and_answer_serializers_require_backend_fields(self):
        question_serializer = QuestionSerializer(data={"body": "Missing title and subject"})
        answer_serializer = AnswerSerializer(data={})

        self.assertFalse(question_serializer.is_valid())
        self.assertTrue({"title", "subject"}.issubset(question_serializer.errors))
        self.assertFalse(answer_serializer.is_valid())
        self.assertIn("body", answer_serializer.errors)

    def test_education_and_interaction_serializers_are_constructible(self):
        student_interest = StudentInterest.objects.create(student_profile=self.profile, interest=self.interest)
        saved = SavedResource.objects.create(user=self.user, resource=self.resource)
        resource_upvote = ResourceUpvote.objects.create(user=self.user, resource=self.resource)
        question_upvote = QuestionUpvote.objects.create(user=self.user, question=self.question)
        answer_upvote = AnswerUpvote.objects.create(user=self.user, answer=self.answer)
        notification = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.RESOURCE_UPVOTED,
            content_object=self.resource,
        )

        self.assertEqual(EducationBackgroundSerializer(self.background).data["slug"], "serializer-engineering")
        self.assertEqual(CourseSerializer(self.course).data["name"], "B.Tech")
        self.assertEqual(AcademicLevelSerializer(self.level).data["level_type"], "semester")
        self.assertEqual(InterestSerializer(self.interest).data["name"], "Physics")
        self.assertEqual(StudentInterestSerializer(student_interest).data["interest_detail"]["slug"], "serializer-physics")
        self.assertEqual(SavedResourceSerializer(saved).data["resource"], self.resource.pk)
        self.assertEqual(ResourceUpvoteSerializer(resource_upvote).data["resource"], self.resource.pk)
        self.assertEqual(QuestionUpvoteSerializer(question_upvote).data["question"], self.question.pk)
        self.assertEqual(AnswerUpvoteSerializer(answer_upvote).data["answer"], self.answer.pk)
        self.assertFalse(NotificationSerializer(notification).data["is_read"])

    def test_serializer_validation_rejects_link_without_url(self):
        serializer = ResourceSerializer(
            data={"title": "Link", "subject": "Physics", "resource_type": Resource.ResourceType.LINK}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("external_url", serializer.errors)

    def test_profile_serializer_validates_education_consistency(self):
        serializer = StudentProfileSerializer(
            self.profile,
            data={"course": self.course.pk, "academic_level": self.level.pk},
            partial=True,
        )

        self.assertTrue(serializer.is_valid())

    def test_registration_creates_safe_user_and_profile(self):
        serializer = RegistrationSerializer(
            data={
                "name": "New Student",
                "email": "new.student@example.com",
                "password": "A-strong-registration-password-42!",
                "college": self.background.name,
                "course": self.course.name,
                "semester": self.level.name,
                "user_id": self.other_user.pk,
                "is_staff": True,
                "contribution_points": 999,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        profile = StudentProfile.objects.get(user=user)

        self.assertTrue(user.check_password("A-strong-registration-password-42!"))
        self.assertNotEqual(user.password, "A-strong-registration-password-42!")
        self.assertEqual(user.email, "new.student@example.com")
        self.assertEqual(user.username, "newstudent")
        self.assertIsNone(profile.education_background)
        self.assertIsNone(profile.course)
        self.assertIsNone(profile.academic_level)
        self.assertFalse(user.is_staff)
        self.assertEqual(profile.contribution_points, 0)

        response_data = serializer.data
        self.assertIn("user", response_data)
        self.assertIn("profile", response_data)
        self.assertNotIn("password", response_data)
        self.assertNotIn("access", response_data)
        self.assertNotIn("refresh", response_data)

    def test_registration_rejects_duplicate_email_and_weak_password(self):
        User.objects.create_user(
            username="existing-email",
            email="existing@example.com",
            password="A-strong-existing-password-42!",
        )
        duplicate = RegistrationSerializer(
            data={
                "name": "Duplicate",
                "email": "EXISTING@example.com",
                "password": "A-strong-registration-password-42!",
                "college": self.background.name,
                "course": self.course.name,
                "semester": self.level.name,
            }
        )
        weak = RegistrationSerializer(
            data={
                "name": "Weak Password",
                "email": "weak@example.com",
                "password": "password",
                "college": self.background.name,
                "course": self.course.name,
                "semester": self.level.name,
            }
        )

        self.assertFalse(duplicate.is_valid())
        self.assertIn("email", duplicate.errors)
        self.assertFalse(weak.is_valid())
        self.assertIn("password", weak.errors)

    def test_registration_accepts_location_and_ignores_legacy_education_fields(self):
        serializer = RegistrationSerializer(
            data={
                "name": "Unknown Education",
                "email": "unknown.education@example.com",
                "password": "A-strong-registration-password-42!",
                "college": "IIT Delhi",
                "course": "Does Not Exist",
                "semester": self.level.name,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.student_profile.college, "IIT Delhi")
        self.assertIsNone(user.student_profile.course)

    def test_registration_persists_a_free_text_college(self):
        serializer = RegistrationSerializer(
            data={
                "name": "College Student",
                "email": "college.student@example.com",
                "password": "A-strong-registration-password-42!",
                "college": "IIT Delhi",
                "course": self.course.name,
                "semester": self.level.name,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.student_profile.college, "IIT Delhi")
        self.assertIsNone(user.student_profile.education_background)


class APIViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(
            username="api-user", email="api-user@example.com", password="not-used-in-test"
        )
        cls.other_user = User.objects.create_user(
            username="api-peer", email="api-peer@example.com", password="not-used-in-test"
        )
        cls.background = EducationBackground.objects.create(name="API Engineering", slug="api-engineering")
        cls.course = Course.objects.create(
            education_background=cls.background, name="API B.Tech", slug="api-btech"
        )
        cls.level = AcademicLevel.objects.create(
            course=cls.course,
            name="1st Year",
            slug="api-year-1",
            level_type=AcademicLevel.LevelType.YEAR,
            order=1,
        )
        cls.other_background = EducationBackground.objects.create(
            name="API Commerce", slug="api-commerce"
        )
        cls.other_course = Course.objects.create(
            education_background=cls.other_background,
            name="API B.Com",
            slug="api-bcom",
        )
        cls.other_level = AcademicLevel.objects.create(
            course=cls.other_course,
            name="2nd Year",
            slug="api-bcom-year-2",
            level_type=AcademicLevel.LevelType.YEAR,
            order=2,
        )
        cls.course_interest = Interest.objects.create(
            name="API Engineering Interest",
            slug="api-engineering-interest",
        )
        cls.other_course_interest = Interest.objects.create(
            name="API Commerce Interest",
            slug="api-commerce-interest",
        )
        cls.course.interests.add(cls.course_interest)
        cls.other_course.interests.add(cls.other_course_interest)
        cls.resource = Resource.objects.create(
            title="API notes",
            uploader=cls.user,
            subject="Physics",
            academic_level=cls.level,
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        cls.video = Video.objects.create(
            title="API video",
            uploader=cls.user,
            youtube_video_id="LmNoPqRsTuV",
            subject="Physics",
            status=PublicationStatus.PUBLISHED,
        )
        cls.question = Question.objects.create(
            title="API question", body="Question body", author=cls.user, subject="Physics"
        )
        cls.answer = Answer.objects.create(
            question=cls.question, author=cls.user, body="API answer"
        )
        StudentProfile.objects.create(
            user=cls.user,
            education_background=cls.background,
            course=cls.course,
            academic_level=cls.level,
        )
        Notification.objects.create(
            recipient=cls.user,
            actor=cls.other_user,
            notification_type=Notification.NotificationType.RESOURCE_UPVOTED,
            content_object=cls.resource,
        )
        Notification.objects.create(
            recipient=cls.other_user,
            actor=cls.user,
            notification_type=Notification.NotificationType.RESOURCE_SAVED,
            content_object=cls.resource,
        )

    def setUp(self) -> None:
        self.client = APIClient()

    def create_published_resource(self, **overrides):
        values = {
            "title": "Filtered resource",
            "uploader": self.user,
            "subject": "Physics",
            "resource_type": Resource.ResourceType.NOTES,
            "status": PublicationStatus.PUBLISHED,
        }
        values.update(overrides)
        return Resource.objects.create(**values)

    def onboarding_payload(self, **overrides):
        payload = {
            "education_background": self.background.pk,
            "course": self.course.pk,
            "academic_level": self.level.pk,
            "interests": [self.course_interest.pk],
        }
        payload.update(overrides)
        return payload

    def test_public_read_routes_resolve(self):
        route_expectations = (
            ("/api/users/", 200),
            ("/api/users/api-user/", 200),
            ("/api/education/backgrounds/", 200),
            ("/api/education/courses/", 200),
            ("/api/education/academic-levels/", 200),
            ("/api/education/levels/", 200),
            ("/api/resources/", 200),
            (f"/api/resources/{self.resource.slug}/", 200),
            ("/api/videos/", 200),
            (f"/api/videos/{self.video.slug}/", 200),
            ("/api/questions/", 200),
            (f"/api/questions/{self.question.slug}/", 200),
            (f"/api/questions/{self.question.pk}/answers/", 200),
            (f"/api/questions/{self.question.pk}/answers/{self.answer.pk}/", 200),
            ("/api/education/interests/", 200),
        )

        for path, expected_status in route_expectations:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, expected_status)

    def test_backgrounds_are_public_and_return_active_catalog_records(self):
        inactive = EducationBackground.objects.create(
            name="Inactive Background", slug="inactive-background", is_active=False
        )

        response = self.client.get("/api/education/backgrounds/")

        self.assertEqual(response.status_code, 200)
        result_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(self.background.pk, result_ids)
        self.assertNotIn(inactive.pk, result_ids)

    def test_courses_are_filtered_by_background_and_invalid_background_is_empty(self):
        response = self.client.get(
            "/api/education/courses/", {"background": self.background.slug}
        )
        invalid = self.client.get(
            "/api/education/courses/", {"background": "does-not-exist"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.course.pk])
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.data["results"], [])

    def test_levels_are_filtered_by_course_and_preserve_old_route(self):
        response = self.client.get("/api/education/levels/", {"course": self.course.slug})
        legacy_response = self.client.get(
            "/api/education/academic-levels/", {"course": self.course.slug}
        )
        wrong_course = self.client.get(
            "/api/education/levels/", {"course": self.other_course.slug}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.level.pk])
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual([item["id"] for item in legacy_response.data["results"]], [self.level.pk])
        self.assertEqual(wrong_course.status_code, 200)
        self.assertEqual(
            [item["id"] for item in wrong_course.data["results"]], [self.other_level.pk]
        )

    def test_interests_are_filtered_by_course_and_invalid_course_is_empty(self):
        response = self.client.get("/api/education/interests/", {"course": self.course.slug})
        invalid = self.client.get(
            "/api/education/interests/", {"course": "does-not-exist"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]], [self.course_interest.pk]
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.data["results"], [])

    def test_dynamic_onboarding_chain_supports_all_background_categories(self):
        category_specs = (
            ("Science", "science"),
            ("Commerce", "commerce"),
            ("Arts/Humanities", "arts-humanities"),
            ("Engineering", "engineering-dynamic"),
            ("CS/IT", "cs-it"),
            ("Medical", "medical"),
            ("Management", "management-dynamic"),
            ("Law", "law"),
            ("Education", "education"),
            ("Design", "design"),
            ("School", "school-dynamic"),
            ("Diploma/Vocational", "diploma-vocational"),
            ("Other", "other-dynamic"),
        )
        self.client.force_authenticate(user=self.user)

        for name, slug in category_specs:
            background, _ = EducationBackground.objects.get_or_create(
                slug=slug, defaults={"name": name}
            )
            course = Course.objects.create(
                education_background=background,
                name=f"{name} Program",
                slug=f"{slug}-program",
            )
            level = AcademicLevel.objects.create(
                course=course,
                name="Level 1",
                slug=f"{slug}-level-1",
                level_type=AcademicLevel.LevelType.LEVEL,
                order=1,
            )
            interest = Interest.objects.create(
                name=f"{name} Interest",
                slug=f"{slug}-interest",
            )
            course.interests.add(interest)

            with self.subTest(category=name):
                course_response = self.client.get(
                    "/api/education/courses/", {"background": background.slug}
                )
                level_response = self.client.get(
                    "/api/education/levels/", {"course": course.slug}
                )
                interest_response = self.client.get(
                    "/api/education/interests/", {"course": course.slug}
                )
                onboarding_response = self.client.post(
                    "/api/users/onboarding/",
                    {
                        "education_background": background.pk,
                        "course": course.pk,
                        "academic_level": level.pk,
                        "interests": [interest.pk],
                        **(
                            {"custom_background": "Custom Other Background"}
                            if name == "Other"
                            else {}
                        ),
                    },
                    format="json",
                )

                self.assertIn(
                    course.pk, [item["id"] for item in course_response.data["results"]]
                )
                self.assertEqual(
                    [item["id"] for item in level_response.data["results"]], [level.pk]
                )
                self.assertEqual(
                    [item["id"] for item in interest_response.data["results"]], [interest.pk]
                )
                self.assertEqual(onboarding_response.status_code, 200)
                self.assertEqual(
                    onboarding_response.data["profile"]["education_background"], background.pk
                )

    def test_empty_query_values_are_safe_and_catalog_reads_do_not_require_authentication(self):
        courses = self.client.get("/api/education/courses/", {"background": ""})
        levels = self.client.get("/api/education/levels/", {"course": ""})
        interests = self.client.get("/api/education/interests/", {"course": ""})

        self.assertEqual(courses.status_code, 200)
        self.assertEqual(levels.status_code, 200)
        self.assertEqual(interests.status_code, 200)
        self.assertEqual(courses.data["results"], [])
        self.assertEqual(levels.data["results"], [])
        self.assertEqual(interests.data["results"], [])

    def test_authenticated_user_can_submit_valid_onboarding(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/users/onboarding/", self.onboarding_payload(), format="json"
        )

        self.assertEqual(response.status_code, 200)
        profile = StudentProfile.objects.get(user=self.user)
        profile.refresh_from_db()
        self.assertTrue(profile.onboarding_completed)
        self.assertIsNotNone(profile.onboarding_completed_at)
        self.assertEqual(profile.education_background_id, self.background.pk)
        self.assertEqual(profile.course_id, self.course.pk)
        self.assertEqual(profile.academic_level_id, self.level.pk)
        self.assertEqual(
            list(profile.student_interests.values_list("interest_id", flat=True)),
            [self.course_interest.pk],
        )
        self.assertTrue(response.data["profile"]["onboarding_completed"])
        self.assertEqual(
            [item["interest"] for item in response.data["student_interests"]],
            [self.course_interest.pk],
        )

    def test_onboarding_rejects_missing_required_fields(self):
        self.client.force_authenticate(user=self.user)

        for field in ("education_background", "course", "academic_level"):
            with self.subTest(field=field):
                payload = self.onboarding_payload()
                payload.pop(field)
                response = self.client.post("/api/users/onboarding/", payload, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_onboarding_rejects_more_than_eight_interests(self):
        extra_interests = [
            Interest.objects.create(
                name=f"Onboarding interest {index}",
                slug=f"onboarding-interest-{index}",
            )
            for index in range(8)
        ]
        self.course.interests.add(*extra_interests)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding_payload(
                interests=[self.course_interest.pk, *(interest.pk for interest in extra_interests)]
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("interests", response.data)

    @patch("apps.users.serializers.StudentInterest.objects.bulk_create")
    def test_onboarding_persistence_is_atomic(self, bulk_create_mock):
        bulk_create_mock.side_effect = RuntimeError("student interests unavailable")
        self.client.force_authenticate(user=self.user)
        profile = StudentProfile.objects.get(user=self.user)
        original_state = (
            profile.education_background_id,
            profile.course_id,
            profile.academic_level_id,
            profile.onboarding_completed,
            profile.onboarding_completed_at,
        )
        original_interest_ids = list(
            StudentInterest.objects.filter(student_profile=profile)
            .order_by("pk")
            .values_list("interest_id", flat=True)
        )

        response = self.client.post(
            "/api/users/onboarding/", self.onboarding_payload(), format="json"
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {"detail": "Something went wrong. Please try again."})

        profile.refresh_from_db()
        self.assertEqual(
            (
                profile.education_background_id,
                profile.course_id,
                profile.academic_level_id,
                profile.onboarding_completed,
                profile.onboarding_completed_at,
            ),
            original_state,
        )
        self.assertEqual(
            list(
                StudentInterest.objects.filter(student_profile=profile)
                .order_by("pk")
                .values_list("interest_id", flat=True)
            ),
            original_interest_ids,
        )

    def test_onboarding_rejects_invalid_background_course_combination(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding_payload(
                education_background=self.background.pk,
                course=self.other_course.pk,
                academic_level=self.other_level.pk,
                interests=[self.other_course_interest.pk],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("course", response.data)
        self.assertFalse(StudentProfile.objects.get(user=self.user).onboarding_completed)
        self.assertFalse(StudentInterest.objects.filter(student_profile__user=self.user).exists())

    def test_onboarding_rejects_invalid_course_level_combination(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding_payload(academic_level=self.other_level.pk),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("academic_level", response.data)
        self.assertFalse(StudentProfile.objects.get(user=self.user).onboarding_completed)

    def test_onboarding_rejects_interest_not_valid_for_selected_course(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding_payload(interests=[self.other_course_interest.pk]),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("interests", response.data)
        self.assertFalse(StudentProfile.objects.get(user=self.user).onboarding_completed)

    def test_onboarding_requires_authentication(self):
        response = self.client.post(
            "/api/users/onboarding/", self.onboarding_payload(), format="json"
        )

        self.assertEqual(response.status_code, 401)

    def test_onboarding_rejects_user_identity_and_completion_spoofing(self):
        self.client.force_authenticate(user=self.user)
        payload = self.onboarding_payload(
            user_id=self.other_user.pk,
            username=self.other_user.username,
            onboarding_completed=False,
        )

        response = self.client.post("/api/users/onboarding/", payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("user_id", response.data)
        self.assertIn("username", response.data)
        self.assertIn("onboarding_completed", response.data)
        self.assertFalse(StudentProfile.objects.filter(user=self.other_user).exists())
        self.assertFalse(StudentProfile.objects.get(user=self.user).onboarding_completed)

    def test_repeated_valid_onboarding_replaces_selected_interests(self):
        self.client.force_authenticate(user=self.user)
        replacement_interest = Interest.objects.create(
            name="API Replacement Interest", slug="api-replacement-interest"
        )
        self.course.interests.add(replacement_interest)

        first_response = self.client.post(
            "/api/users/onboarding/", self.onboarding_payload(), format="json"
        )
        first_timestamp = StudentProfile.objects.get(user=self.user).onboarding_completed_at
        second_response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding_payload(interests=[replacement_interest.pk]),
            format="json",
        )

        profile = StudentProfile.objects.get(user=self.user)
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertTrue(profile.onboarding_completed)
        self.assertEqual(profile.onboarding_completed_at, first_timestamp)
        self.assertEqual(
            list(profile.student_interests.values_list("interest_id", flat=True)),
            [replacement_interest.pk],
        )

    def test_invalid_onboarding_submission_rolls_back_and_preserves_previous_state(self):
        self.client.force_authenticate(user=self.user)
        first_response = self.client.post(
            "/api/users/onboarding/", self.onboarding_payload(), format="json"
        )
        profile = StudentProfile.objects.get(user=self.user)
        original_timestamp = profile.onboarding_completed_at

        invalid_response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding_payload(
                course=self.other_course.pk,
                academic_level=self.other_level.pk,
                interests=[self.other_course_interest.pk],
            ),
            format="json",
        )

        profile.refresh_from_db()
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(invalid_response.status_code, 400)
        self.assertTrue(profile.onboarding_completed)
        self.assertEqual(profile.education_background_id, self.background.pk)
        self.assertEqual(profile.course_id, self.course.pk)
        self.assertEqual(profile.academic_level_id, self.level.pk)
        self.assertEqual(profile.onboarding_completed_at, original_timestamp)
        self.assertEqual(
            list(profile.student_interests.values_list("interest_id", flat=True)),
            [self.course_interest.pk],
        )

    def test_resource_search_is_case_insensitive_and_ranked_without_tag_duplicates(self):
        title_match = Resource.objects.create(
            title="Java concurrency notes",
            uploader=self.user,
            subject="Physics",
            topic="Mechanics",
            description="Unrelated material",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        subject_match = Resource.objects.create(
            title="Collections guide",
            uploader=self.user,
            subject="Java",
            topic="Collections",
            description="Unrelated material",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        topic_match = Resource.objects.create(
            title="Sorting guide",
            uploader=self.user,
            subject="Physics",
            topic="Java algorithms",
            description="Unrelated material",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        description_match = Resource.objects.create(
            title="Algorithms guide",
            uploader=self.user,
            subject="Physics",
            topic="Sorting",
            description="Java examples and explanations",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        tag_match = Resource.objects.create(
            title="Algorithms reference",
            uploader=self.user,
            subject="Physics",
            topic="Sorting",
            description="Unrelated material",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        tag_match.tags.add(
            Tag.objects.create(name="Java", slug="java"),
            Tag.objects.create(name="Java Core", slug="java-core"),
        )

        response = self.client.get("/api/resources/?search=JAVA")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual(response.data["count"], 5)
        result_ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(result_ids.count(tag_match.pk), 1)
        self.assertEqual(result_ids[0], title_match.pk)
        self.assertLess(result_ids.index(subject_match.pk), result_ids.index(description_match.pk))
        self.assertLess(result_ids.index(topic_match.pk), result_ids.index(description_match.pk))
        self.assertLess(result_ids.index(description_match.pk), result_ids.index(tag_match.pk))

    def test_resource_search_uses_latest_as_tie_breaker(self):
        older_match = Resource.objects.create(
            title="Java older notes",
            uploader=self.user,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        newer_match = Resource.objects.create(
            title="Java newer notes",
            uploader=self.user,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        now = timezone.now()
        Resource.objects.filter(pk=older_match.pk).update(created_at=now - timedelta(days=1))
        Resource.objects.filter(pk=newer_match.pk).update(created_at=now)

        response = self.client.get("/api/resources/?search=java")

        self.assertEqual(response.status_code, 200)
        result_ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(result_ids[:2], [newer_match.pk, older_match.pk])

    def test_resource_search_uses_existing_pagination(self):
        for index in range(StudyMatePagination.page_size + 1):
            Resource.objects.create(
                title=f"Java search result {index}",
                uploader=self.user,
                subject="Physics",
                resource_type=Resource.ResourceType.NOTES,
                status=PublicationStatus.PUBLISHED,
            )

        first_page = self.client.get("/api/resources/?search=java&page=1")
        second_page = self.client.get("/api/resources/?search=java&page=2")

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(first_page.data["count"], StudyMatePagination.page_size + 1)
        self.assertEqual(len(first_page.data["results"]), StudyMatePagination.page_size)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertIsNotNone(first_page.data["next"])
        self.assertIsNotNone(second_page.data["previous"])
        self.assertTrue(
            set(item["id"] for item in first_page.data["results"]).isdisjoint(
                item["id"] for item in second_page.data["results"]
            )
        )

    def test_resource_search_preserves_published_and_owner_visibility(self):
        hidden_resource = Resource.objects.create(
            title="Private Java notes",
            uploader=self.user,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.DRAFT,
        )

        anonymous_response = self.client.get("/api/resources/?search=java")
        self.client.force_authenticate(user=self.other_user)
        other_user_response = self.client.get("/api/resources/?search=java")
        self.client.force_authenticate(user=self.user)
        owner_response = self.client.get("/api/resources/?search=java")

        self.assertNotIn(hidden_resource.pk, [item["id"] for item in anonymous_response.data["results"]])
        self.assertNotIn(hidden_resource.pk, [item["id"] for item in other_user_response.data["results"]])
        self.assertIn(hidden_resource.pk, [item["id"] for item in owner_response.data["results"]])

    def test_resource_filters_support_each_resource_field(self):
        subject_match = self.create_published_resource(subject="Computer Science")
        topic_match = self.create_published_resource(topic="Data Structures")
        type_match = self.create_published_resource(resource_type=Resource.ResourceType.PDF)
        other_level = AcademicLevel.objects.create(
            course=self.course,
            name="2nd Year",
            slug="api-year-2",
            level_type=AcademicLevel.LevelType.YEAR,
            order=2,
        )
        academic_match = self.create_published_resource(academic_level=other_level)
        difficulty_match = self.create_published_resource(difficulty=Resource.Difficulty.BEGINNER)

        filter_cases = (
            ("subject", "computer science", subject_match),
            ("topic", "data structures", topic_match),
            ("resource_type", "PDF", type_match),
            ("academic_level", str(other_level.pk), academic_match),
            ("difficulty", "Beginner", difficulty_match),
        )
        for parameter, value, expected_resource in filter_cases:
            with self.subTest(parameter=parameter):
                response = self.client.get("/api/resources/", {parameter: value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [item["id"] for item in response.data["results"]],
                    [expected_resource.pk],
                )

    def test_resource_tag_filter_matches_case_insensitively_without_duplicates(self):
        tag = Tag.objects.create(name="Java", slug="java")
        matching_resource = self.create_published_resource(title="Tagged resource")
        matching_resource.tags.add(tag)

        response = self.client.get("/api/resources/?tags=JAVA")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual([item["id"] for item in response.data["results"]], [matching_resource.pk])

    def test_resource_filters_can_be_combined(self):
        tag = Tag.objects.create(name="Java", slug="java")
        matching_resource = self.create_published_resource(
            subject="Computer Science",
            topic="Algorithms",
            resource_type=Resource.ResourceType.PDF,
            academic_level=self.level,
            difficulty=Resource.Difficulty.INTERMEDIATE,
        )
        matching_resource.tags.add(tag)
        self.create_published_resource(
            subject="Computer Science",
            topic="Databases",
            resource_type=Resource.ResourceType.PDF,
            academic_level=self.level,
            difficulty=Resource.Difficulty.INTERMEDIATE,
        )

        response = self.client.get(
            "/api/resources/",
            {
                "subject": "Computer Science",
                "topic": "Algorithms",
                "resource_type": "pdf",
                "academic_level": str(self.level.pk),
                "difficulty": "intermediate",
                "tags": "java",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [matching_resource.pk])

    def test_resource_filters_return_empty_results_for_invalid_values(self):
        invalid_filters = (
            {"resource_type": "not-a-resource-type"},
            {"difficulty": "not-a-difficulty"},
            {"academic_level": "not-an-academic-level"},
            {"tags": "unknown-tag"},
        )

        for query_params in invalid_filters:
            with self.subTest(query_params=query_params):
                response = self.client.get("/api/resources/", query_params)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
                self.assertEqual(response.data["count"], 0)
                self.assertEqual(response.data["results"], [])
                self.assertIsNone(response.data["next"])
                self.assertIsNone(response.data["previous"])

    def test_resource_search_and_filters_are_combined_in_the_database(self):
        matching_resource = self.create_published_resource(
            title="Java algorithms",
            subject="Computer Science",
        )
        self.create_published_resource(title="Java physics", subject="Physics")

        response = self.client.get(
            "/api/resources/",
            {"search": "java", "subject": "computer science"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [matching_resource.pk])

    def test_resource_filters_work_with_existing_pagination(self):
        for index in range(StudyMatePagination.page_size + 1):
            self.create_published_resource(
                title=f"Computer Science resource {index}",
                subject="Computer Science",
            )

        first_page = self.client.get("/api/resources/?subject=computer%20science&page=1")
        second_page = self.client.get("/api/resources/?subject=computer%20science&page=2")

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(first_page.data["count"], StudyMatePagination.page_size + 1)
        self.assertEqual(len(first_page.data["results"]), StudyMatePagination.page_size)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertTrue(
            set(item["id"] for item in first_page.data["results"]).isdisjoint(
                item["id"] for item in second_page.data["results"]
            )
        )

    def test_resource_pagination_supports_pages_one_two_and_three(self):
        resources = [
            self.create_published_resource(
                title=f"Pagination resource {index}",
                subject="Pagination Subject",
            )
            for index in range((StudyMatePagination.page_size * 2) + 1)
        ]

        pages = [
            self.client.get(f"/api/resources/?subject=Pagination%20Subject&page={page}")
            for page in (1, 2, 3)
        ]

        for response in pages:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
            self.assertEqual(response.data["count"], len(resources))
        self.assertEqual(len(pages[0].data["results"]), StudyMatePagination.page_size)
        self.assertEqual(len(pages[1].data["results"]), StudyMatePagination.page_size)
        self.assertEqual(len(pages[2].data["results"]), 1)
        self.assertIsNone(pages[0].data["previous"])
        self.assertIsNotNone(pages[0].data["next"])
        self.assertIsNotNone(pages[1].data["previous"])
        self.assertIsNotNone(pages[1].data["next"])
        self.assertIsNotNone(pages[2].data["previous"])
        self.assertIsNone(pages[2].data["next"])

        page_ids = [
            item["id"]
            for response in pages
            for item in response.data["results"]
        ]
        self.assertEqual(set(page_ids), {resource.pk for resource in resources})
        self.assertEqual(len(page_ids), len(set(page_ids)))

    def test_resource_pagination_returns_not_found_beyond_available_results(self):
        self.create_published_resource(subject="Only Resource")

        response = self.client.get("/api/resources/?subject=Only%20Resource&page=2")

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.data)

    def test_resource_pagination_rejects_invalid_page_numbers_safely(self):
        response = self.client.get("/api/resources/?page=not-a-number")

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.data)

    def test_resource_pagination_combines_with_search_filters_and_ordering(self):
        resources = [
            self.create_published_resource(
                title=f"Java pagination resource {index}",
                subject="Paged Computer Science",
            )
            for index in range(StudyMatePagination.page_size + 1)
        ]
        base_time = timezone.now()
        for index, resource in enumerate(resources):
            Resource.objects.filter(pk=resource.pk).update(
                created_at=base_time + timedelta(seconds=index)
            )

        response = self.client.get(
            "/api/resources/",
            {
                "search": "java",
                "subject": "paged computer science",
                "ordering": "latest",
                "page": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], len(resources))
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], resources[0].pk)

    def test_resource_ordering_latest_uses_created_at_with_stable_ties(self):
        older_resource = self.create_published_resource(title="Older resource")
        newer_resource = self.create_published_resource(title="Newer resource")
        now = timezone.now()
        Resource.objects.filter(pk=older_resource.pk).update(created_at=now - timedelta(days=1))
        Resource.objects.filter(pk=newer_resource.pk).update(created_at=now)

        response = self.client.get("/api/resources/?ordering=latest")

        self.assertEqual(response.status_code, 200)
        result_ids = [item["id"] for item in response.data["results"]]
        self.assertLess(result_ids.index(newer_resource.pk), result_ids.index(older_resource.pk))

    def test_resource_ordering_popular_uses_view_events(self):
        less_popular = self.create_published_resource(title="Less popular")
        more_popular = self.create_published_resource(title="More popular")
        ResourceView.objects.create(resource=less_popular, user=self.user)
        ResourceView.objects.create(resource=more_popular, user=self.user)
        ResourceView.objects.create(resource=more_popular, user=self.other_user)

        response = self.client.get("/api/resources/?ordering=popular")

        self.assertEqual(response.status_code, 200)
        result_ids = [item["id"] for item in response.data["results"]]
        self.assertLess(result_ids.index(more_popular.pk), result_ids.index(less_popular.pk))

    def test_resource_ordering_top_rated_uses_existing_upvotes(self):
        lower_rated = self.create_published_resource(title="Lower rated")
        higher_rated = self.create_published_resource(title="Higher rated")
        ResourceUpvote.objects.create(resource=lower_rated, user=self.user)
        ResourceUpvote.objects.create(resource=higher_rated, user=self.user)
        ResourceUpvote.objects.create(resource=higher_rated, user=self.other_user)

        response = self.client.get("/api/resources/?ordering=top_rated")

        self.assertEqual(response.status_code, 200)
        result_ids = [item["id"] for item in response.data["results"]]
        self.assertLess(result_ids.index(higher_rated.pk), result_ids.index(lower_rated.pk))

    def test_resource_ordering_most_downloaded_uses_download_events(self):
        less_downloaded = self.create_published_resource(title="Less downloaded")
        more_downloaded = self.create_published_resource(title="More downloaded")
        ResourceDownload.objects.create(resource=less_downloaded, user=self.user)
        ResourceDownload.objects.create(resource=more_downloaded, user=self.user)
        ResourceDownload.objects.create(resource=more_downloaded, user=self.other_user)

        response = self.client.get("/api/resources/?ordering=most_downloaded")

        self.assertEqual(response.status_code, 200)
        result_ids = [item["id"] for item in response.data["results"]]
        self.assertLess(result_ids.index(more_downloaded.pk), result_ids.index(less_downloaded.pk))

    def test_resource_ordering_unsupported_value_uses_default_ordering(self):
        older_resource = self.create_published_resource(title="Older default resource")
        newer_resource = self.create_published_resource(title="Newer default resource")
        now = timezone.now()
        Resource.objects.filter(pk=older_resource.pk).update(created_at=now - timedelta(days=1))
        Resource.objects.filter(pk=newer_resource.pk).update(created_at=now)

        response = self.client.get("/api/resources/?ordering=not-a-supported-order")

        self.assertEqual(response.status_code, 200)
        result_ids = [item["id"] for item in response.data["results"]]
        self.assertLess(result_ids.index(newer_resource.pk), result_ids.index(older_resource.pk))

    def test_resource_ordering_combines_with_search_filters_and_pagination(self):
        less_popular = self.create_published_resource(
            title="Java algorithms older",
            subject="Computer Science",
        )
        more_popular = self.create_published_resource(
            title="Java algorithms newer",
            subject="Computer Science",
        )
        ResourceView.objects.create(resource=less_popular, user=self.user)
        ResourceView.objects.create(resource=more_popular, user=self.user)
        ResourceView.objects.create(resource=more_popular, user=self.other_user)
        self.create_published_resource(title="Java physics", subject="Physics")

        response = self.client.get(
            "/api/resources/",
            {
                "search": "java",
                "subject": "computer science",
                "ordering": "popular",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [more_popular.pk, less_popular.pk])

    def test_non_published_content_is_hidden_from_public_and_other_users(self):
        draft_resource = Resource.objects.create(
            title="Private API notes",
            uploader=self.user,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.DRAFT,
        )
        draft_video = Video.objects.create(
            title="Private API video",
            uploader=self.user,
            youtube_video_id="WxYz0123456",
            subject="Physics",
            status=PublicationStatus.DRAFT,
        )
        draft_question = Question.objects.create(
            title="Private API question",
            body="Private question body",
            author=self.user,
            subject="Physics",
            status=PublicationStatus.DRAFT,
        )
        draft_answer = Answer.objects.create(
            question=draft_question,
            author=self.user,
            body="Private answer",
            status=PublicationStatus.DRAFT,
        )

        draft_paths = (
            f"/api/resources/{draft_resource.slug}/",
            f"/api/videos/{draft_video.slug}/",
            f"/api/questions/{draft_question.slug}/",
            f"/api/questions/{draft_question.pk}/answers/{draft_answer.pk}/",
        )
        for path in draft_paths:
            with self.subTest(path=path, viewer="anonymous"):
                self.assertEqual(self.client.get(path).status_code, 404)

        self.client.force_authenticate(user=self.other_user)
        for path in draft_paths:
            with self.subTest(path=path, viewer="other-user"):
                self.assertEqual(self.client.get(path).status_code, 404)

        self.client.force_authenticate(user=self.user)
        for path in draft_paths:
            with self.subTest(path=path, viewer="owner"):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_authenticated_user_cannot_answer_hidden_question_by_id(self):
        draft_question = Question.objects.create(
            title="Hidden question",
            body="Hidden question body",
            author=self.user,
            subject="Physics",
            status=PublicationStatus.DRAFT,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            f"/api/questions/{draft_question.pk}/answers/",
            {"body": "Answering a hidden question"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_signup_creates_user_profile_and_returns_safe_data(self):
        response = self.client.post(
            "/api/auth/signup/",
            {
                "name": "Signup Student",
                "email": "signup.student@example.com",
                "password": "A-strong-signup-password-42!",
                "college": self.background.name,
                "country": "India",
                "state": "Delhi",
                "city": "New Delhi",
                "course": self.course.name,
                "semester": self.level.name,
                "is_staff": True,
                "user_id": self.other_user.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["email"], "signup.student@example.com")
        self.assertEqual(response.data["profile"]["display_name"], "Signup Student")
        self.assertEqual(response.data["profile"]["country"], "India")
        self.assertEqual(response.data["profile"]["state"], "Delhi")
        self.assertEqual(response.data["profile"]["city"], "New Delhi")
        self.assertNotIn("password", response.data)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)

        user = User.objects.get(email="signup.student@example.com")
        self.assertTrue(user.check_password("A-strong-signup-password-42!"))
        self.assertFalse(user.is_staff)
        self.assertIsNone(user.student_profile.course)
        self.assertEqual(
            (user.student_profile.country, user.student_profile.state, user.student_profile.city),
            ("India", "Delhi", "New Delhi"),
        )

    def test_signup_rejects_duplicate_email_and_handles_username_collision(self):
        User.objects.create_user(
            username="signupstudent",
            email="existing.signup@example.com",
            password="A-strong-existing-password-42!",
        )
        duplicate = self.client.post(
            "/api/auth/signup/",
            {
                "name": "Duplicate Signup",
                "email": "EXISTING.SIGNUP@example.com",
                "password": "A-strong-signup-password-42!",
                "college": self.background.name,
                "course": self.course.name,
                "semester": self.level.name,
            },
            format="json",
        )
        collision = self.client.post(
            "/api/auth/signup/",
            {
                "name": "Collision Signup",
                "email": "signup.student@example.com",
                "password": "A-strong-signup-password-42!",
                "college": self.background.name,
                "course": self.course.name,
                "semester": self.level.name,
            },
            format="json",
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("email", duplicate.data)
        self.assertEqual(collision.status_code, 201)
        self.assertEqual(collision.data["user"]["username"], "signupstudent-2")

    def test_signup_rejects_invalid_password_and_malformed_input(self):
        invalid_password = self.client.post(
            "/api/auth/signup/",
            {
                "name": "Invalid Password",
                "email": "invalid.password@example.com",
                "password": "password",
                "college": self.background.name,
                "course": self.course.name,
                "semester": self.level.name,
            },
            format="json",
        )
        malformed = self.client.post(
            "/api/auth/signup/",
            {"email": "malformed@example.com"},
            format="json",
        )

        self.assertEqual(invalid_password.status_code, 400)
        self.assertIn("password", invalid_password.data)
        self.assertEqual(malformed.status_code, 400)
        self.assertIn("name", malformed.data)

    def test_login_sets_http_only_jwt_cookies_and_safe_user_data(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], "api-user@example.com")
        self.assertNotIn("password", response.data)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, response.cookies)
        self.assertTrue(response.cookies[settings.JWT_ACCESS_COOKIE_NAME]["httponly"])
        self.assertTrue(response.cookies[settings.JWT_REFRESH_COOKIE_NAME]["httponly"])
        self.assertEqual(
            response.cookies[settings.JWT_ACCESS_COOKIE_NAME]["samesite"],
            settings.JWT_COOKIE_SAMESITE,
        )

    def test_login_rejects_invalid_credentials_without_account_enumeration(self):
        invalid_password = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "wrong-password"},
            format="json",
        )
        unknown_email = self.client.post(
            "/api/auth/login/",
            {"email": "missing@example.com", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(invalid_password.status_code, 401)
        self.assertEqual(unknown_email.status_code, 401)
        self.assertEqual(invalid_password.data, unknown_email.data)
        self.assertEqual(invalid_password.data["detail"], "Invalid email or password.")

    def test_login_cookie_authenticates_request_user(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        notification_response = self.client.get("/api/notifications/")

        self.assertEqual(notification_response.status_code, 200)
        self.assertEqual(
            notification_response.data["results"][0]["recipient"]["username"],
            "api-user",
        )

    def test_authenticated_me_uses_cookie_user_not_query_user_id(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        response = self.client.get(f"/api/auth/me/?user_id={self.other_user.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["username"], "api-user")
        self.assertEqual(response.data["user"]["email"], "api-user@example.com")
        self.assertNotIn("password", response.data)

    def test_current_user_reports_incomplete_onboarding(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["user"]["profile"]["onboarding_completed"])

    def test_current_user_reports_completed_onboarding(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        onboarding_response = self.client.post(
            "/api/users/onboarding/", self.onboarding_payload(), format="json"
        )
        self.assertEqual(onboarding_response.status_code, 200)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["user"]["profile"]["onboarding_completed"])

    def test_logout_and_login_preserve_onboarding_completion(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        onboarding_response = self.client.post(
            "/api/users/onboarding/", self.onboarding_payload(), format="json"
        )
        self.assertEqual(onboarding_response.status_code, 200)
        logout_response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(logout_response.status_code, 204)

        second_login = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        me_response = self.client.get("/api/auth/me/")

        self.assertEqual(second_login.status_code, 200)
        self.assertTrue(second_login.data["user"]["profile"]["onboarding_completed"])
        self.assertEqual(me_response.status_code, 200)
        self.assertTrue(me_response.data["user"]["profile"]["onboarding_completed"])

    def test_another_users_onboarding_state_is_private_and_not_changeable(self):
        other_profile = StudentProfile.objects.create(
            user=self.other_user,
            education_background=self.background,
            course=self.course,
            academic_level=self.level,
            onboarding_completed=True,
            onboarding_completed_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.user)

        profile_response = self.client.get(f"/api/users/{self.other_user.username}/")
        spoof_response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding_payload(user_id=self.other_user.pk),
            format="json",
        )

        other_profile.refresh_from_db()
        self.assertEqual(profile_response.status_code, 200)
        self.assertNotIn("onboarding_completed", profile_response.data)
        self.assertNotIn("onboarding_completed_at", profile_response.data)
        self.assertEqual(spoof_response.status_code, 400)
        self.assertTrue(other_profile.onboarding_completed)

    def test_profile_owner_can_update_supported_fields_only(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/users/{self.user.username}/",
            {
                "display_name": "Updated API User",
                "bio": "A short profile bio.",
                "college": "Updated College",
                "user": self.other_user.pk,
                "contribution_points": 999,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        profile = StudentProfile.objects.get(user=self.user)
        self.assertEqual(profile.display_name, "Updated API User")
        self.assertEqual(profile.bio, "A short profile bio.")
        self.assertEqual(profile.college, "Updated College")
        self.assertEqual(profile.contribution_points, 0)
        self.assertEqual(profile.user_id, self.user.pk)

        self.client.force_authenticate(user=self.other_user)
        forbidden = self.client.patch(
            f"/api/users/{self.user.username}/",
            {"bio": "Unauthorized change"},
            format="json",
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_follow_endpoint_is_authenticated_owner_safe_and_idempotent(self):
        self.client.force_authenticate(user=self.user)

        self_follow = self.client.post(f"/api/users/{self.user.username}/follow/")
        first_follow = self.client.post(f"/api/users/{self.other_user.username}/follow/")
        repeated_follow = self.client.post(f"/api/users/{self.other_user.username}/follow/")

        self.assertEqual(self_follow.status_code, 400)
        self.assertEqual(first_follow.status_code, 201)
        self.assertEqual(repeated_follow.status_code, 200)
        self.assertEqual(
            UserFollow.objects.filter(follower=self.user, following=self.other_user).count(),
            1,
        )
        profile_response = self.client.get(f"/api/users/{self.other_user.username}/")
        self.assertTrue(profile_response.data["is_following"])

        unfollow = self.client.delete(f"/api/users/{self.other_user.username}/follow/")
        self.assertEqual(unfollow.status_code, 200)
        self.assertFalse(UserFollow.objects.filter(follower=self.user, following=self.other_user).exists())

        self.client.force_authenticate(user=None)
        unauthenticated = self.client.post(f"/api/users/{self.other_user.username}/follow/")
        self.assertEqual(unauthenticated.status_code, 401)

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)

    def test_refresh_rotates_access_cookie_without_exposing_tokens(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        old_access = self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME].value

        response = self.client.post("/api/auth/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertNotEqual(
            response.cookies[settings.JWT_ACCESS_COOKIE_NAME].value,
            old_access,
        )
        self.assertTrue(response.cookies[settings.JWT_ACCESS_COOKIE_NAME]["httponly"])

    def test_refresh_rejects_invalid_or_expired_refresh_cookie(self):
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = "not-a-refresh-token"
        invalid_response = self.client.post("/api/auth/refresh/", {}, format="json")

        expired = RefreshToken.for_user(self.user)
        expired["exp"] = 0
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = str(expired)
        expired_response = self.client.post("/api/auth/refresh/", {}, format="json")

        self.assertEqual(invalid_response.status_code, 401)
        self.assertEqual(expired_response.status_code, 401)
        self.assertEqual(invalid_response.data, expired_response.data)
        self.assertEqual(invalid_response.data["detail"], "Invalid or expired refresh token.")

    def test_revoked_refresh_cookie_cannot_be_reused(self):
        if "rest_framework_simplejwt.token_blacklist" not in settings.INSTALLED_APPS:
            self.skipTest("Refresh-token blacklist is enabled only in production configuration.")

        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        refresh_token = RefreshToken(self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME].value)
        refresh_token.blacklist()

        response = self.client.post("/api/auth/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Invalid or expired refresh token.")

    def test_logout_clears_cookies_and_access_is_denied_afterward(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "api-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        logout_response = self.client.post("/api/auth/logout/", {}, format="json")
        me_response = self.client.get("/api/auth/me/")

        self.assertEqual(logout_response.status_code, 204)
        self.assertEqual(str(logout_response.cookies[settings.JWT_ACCESS_COOKIE_NAME]["max-age"]), "0")
        self.assertEqual(str(logout_response.cookies[settings.JWT_REFRESH_COOKIE_NAME]["max-age"]), "0")
        self.assertEqual(me_response.status_code, 401)

    def test_logout_is_idempotent_without_auth_cookies(self):
        response = self.client.post("/api/auth/logout/", {}, format="json")

        self.assertEqual(response.status_code, 204)

    def test_list_endpoints_use_bounded_pagination(self):
        list_paths = (
            "/api/users/",
            "/api/education/backgrounds/",
            "/api/education/courses/",
            "/api/education/academic-levels/",
            "/api/education/interests/",
            "/api/resources/?page_size=1",
            "/api/videos/",
            "/api/questions/",
        )

        for path in list_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
                self.assertLessEqual(len(response.data["results"]), StudyMatePagination.max_page_size)

        self.client.force_authenticate(user=self.user)
        notification_response = self.client.get("/api/notifications/")
        self.assertEqual(notification_response.status_code, 200)
        self.assertEqual(set(notification_response.data), {"count", "next", "previous", "results"})

    def test_detail_endpoints_are_not_paginated(self):
        response = self.client.get(f"/api/resources/{self.resource.slug}/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.data)
        self.assertNotIn("results", response.data)

    def test_page_size_is_controlled(self):
        response = self.client.get("/api/resources/?page_size=1000")

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["results"]), StudyMatePagination.max_page_size)

    def test_authenticated_resource_video_question_writes_use_request_owner(self):
        self.client.force_authenticate(user=self.user)

        resource_response = self.client.post(
            "/api/resources/",
            {
                "title": "Created notes",
                "subject": "Chemistry",
                "resource_type": "notes",
                "uploader": self.other_user.pk,
                "user_id": self.other_user.pk,
            },
            format="json",
        )
        video_response = self.client.post(
            "/api/videos/",
            {
                "title": "Created video",
                "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
                "subject": "Chemistry",
            },
            format="json",
        )
        question_response = self.client.post(
            "/api/questions/",
            {
                "title": "Created question",
                "body": "Body",
                "subject": "Chemistry",
                "author": self.other_user.pk,
                "user_id": self.other_user.pk,
            },
            format="json",
        )

        self.assertEqual(resource_response.status_code, 201)
        self.assertEqual(resource_response.data["uploader"]["username"], "api-user")
        self.assertEqual(video_response.status_code, 201)
        self.assertEqual(video_response.data["uploader"]["username"], "api-user")
        self.assertEqual(question_response.status_code, 201)
        self.assertEqual(question_response.data["author"]["username"], "api-user")

    def test_resource_patch_and_delete_use_numeric_id(self):
        self.client.force_authenticate(user=self.user)

        put_response = self.client.put(
            f"/api/resources/{self.resource.pk}/",
            {"title": "Replaced API notes", "subject": "Physics", "resource_type": "notes"},
            format="json",
        )
        patch_response = self.client.patch(
            f"/api/resources/{self.resource.pk}/", {"title": "Updated API notes"}, format="json"
        )
        delete_response = self.client.delete(f"/api/resources/{self.resource.pk}/")

        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(delete_response.status_code, 204)

    def test_authenticated_user_can_save_resource_idempotently(self):
        self.client.force_authenticate(user=self.user)
        save_url = f"/api/resources/{self.resource.pk}/save/"

        first_response = self.client.post(save_url, {"user": self.other_user.pk}, format="json")
        repeated_response = self.client.post(save_url, {}, format="json")

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(repeated_response.status_code, 200)
        self.assertEqual(SavedResource.objects.filter(user=self.user, resource=self.resource).count(), 1)
        self.assertEqual(first_response.data["resource"], self.resource.pk)
        self.assertEqual(first_response.data["user"]["id"], self.user.pk)

    def test_authenticated_user_can_unsave_resource_idempotently(self):
        SavedResource.objects.create(user=self.user, resource=self.resource)
        self.client.force_authenticate(user=self.user)
        save_url = f"/api/resources/{self.resource.pk}/save/"

        first_response = self.client.delete(save_url)
        repeated_response = self.client.delete(save_url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.data, {"saved": False, "resource": self.resource.pk})
        self.assertEqual(repeated_response.status_code, 200)
        self.assertFalse(SavedResource.objects.filter(user=self.user, resource=self.resource).exists())

    def test_resource_save_relationships_are_user_scoped(self):
        self.client.force_authenticate(user=self.user)
        save_url = f"/api/resources/{self.resource.pk}/save/"
        self.client.post(save_url, {}, format="json")

        self.client.force_authenticate(user=self.other_user)
        other_save_response = self.client.post(save_url, {}, format="json")
        self.assertEqual(other_save_response.status_code, 201)
        self.assertEqual(SavedResource.objects.filter(resource=self.resource).count(), 2)

        self.client.delete(save_url)

        self.assertTrue(SavedResource.objects.filter(user=self.user, resource=self.resource).exists())
        self.assertFalse(SavedResource.objects.filter(user=self.other_user, resource=self.resource).exists())

    def test_authenticated_user_can_unsave_resource_when_not_saved(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/resources/{self.resource.pk}/save/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"saved": False, "resource": self.resource.pk})
        self.assertFalse(SavedResource.objects.filter(user=self.user, resource=self.resource).exists())

    def test_authenticated_user_can_list_saved_resources(self):
        SavedResource.objects.create(user=self.user, resource=self.resource)
        unsaved_resource = Resource.objects.create(
            title="Unsaved API notes",
            uploader=self.user,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/saved-resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.resource.pk])
        self.assertNotIn(unsaved_resource.pk, [item["id"] for item in response.data["results"]])

    def test_saved_resource_list_excludes_another_users_saves(self):
        SavedResource.objects.create(user=self.other_user, resource=self.resource)
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/saved-resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_saved_resource_list_is_paginated(self):
        resources = [
            Resource.objects.create(
                title=f"Saved API notes {index}",
                uploader=self.user,
                subject="Physics",
                resource_type=Resource.ResourceType.NOTES,
                status=PublicationStatus.PUBLISHED,
            )
            for index in range(StudyMatePagination.page_size + 1)
        ]
        SavedResource.objects.bulk_create(
            [SavedResource(user=self.user, resource=resource) for resource in resources]
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/saved-resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual(response.data["count"], len(resources))
        self.assertEqual(len(response.data["results"]), StudyMatePagination.page_size)
        self.assertIsNotNone(response.data["next"])

    def test_saved_resource_list_is_empty_when_user_has_no_saves(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/saved-resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_anonymous_user_cannot_save_or_unsave_resource(self):
        save_url = f"/api/resources/{self.resource.pk}/save/"

        save_response = self.client.post(save_url, {}, format="json")
        delete_response = self.client.delete(save_url)

        self.assertEqual(save_response.status_code, 401)
        self.assertEqual(delete_response.status_code, 401)

    def test_anonymous_user_cannot_list_saved_resources(self):
        response = self.client.get("/api/saved-resources/")

        self.assertEqual(response.status_code, 401)

    def test_save_and_unsave_nonexistent_resource_return_not_found(self):
        self.client.force_authenticate(user=self.user)
        save_url = "/api/resources/999999/save/"
        upvote_url = "/api/resources/999999/upvote/"

        save_response = self.client.post(save_url, {}, format="json")
        delete_response = self.client.delete(save_url)
        upvote_response = self.client.post(upvote_url, {}, format="json")
        unvote_response = self.client.delete(upvote_url)

        self.assertEqual(save_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(upvote_response.status_code, 404)
        self.assertEqual(unvote_response.status_code, 404)

    def test_authenticated_user_can_upvote_resource_idempotently(self):
        self.client.force_authenticate(user=self.user)
        upvote_url = f"/api/resources/{self.resource.pk}/upvote/"

        first_response = self.client.post(upvote_url, {}, format="json")
        repeated_response = self.client.post(upvote_url, {}, format="json")

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(repeated_response.status_code, 200)
        self.assertEqual(first_response.data["upvotes"], 1)
        self.assertEqual(repeated_response.data["upvotes"], 1)
        self.assertEqual(ResourceUpvote.objects.filter(resource=self.resource).count(), 1)

    def test_authenticated_user_can_unvote_resource_idempotently(self):
        ResourceUpvote.objects.create(user=self.user, resource=self.resource)
        self.client.force_authenticate(user=self.user)
        upvote_url = f"/api/resources/{self.resource.pk}/upvote/"

        first_response = self.client.delete(upvote_url)
        repeated_response = self.client.delete(upvote_url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.data, {"upvoted": False, "resource": self.resource.pk, "upvotes": 0})
        self.assertEqual(repeated_response.status_code, 200)
        self.assertFalse(ResourceUpvote.objects.filter(user=self.user, resource=self.resource).exists())

    def test_resource_upvotes_are_user_scoped(self):
        upvote_url = f"/api/resources/{self.resource.pk}/upvote/"
        self.client.force_authenticate(user=self.user)
        self.client.post(upvote_url, {}, format="json")

        self.client.force_authenticate(user=self.other_user)
        self.client.delete(upvote_url)

        self.assertTrue(ResourceUpvote.objects.filter(user=self.user, resource=self.resource).exists())
        self.assertFalse(ResourceUpvote.objects.filter(user=self.other_user, resource=self.resource).exists())

        other_response = self.client.post(upvote_url, {}, format="json")
        self.assertEqual(other_response.data["upvotes"], 2)
        self.assertEqual(ResourceUpvote.objects.filter(resource=self.resource).count(), 2)

    def test_anonymous_user_cannot_upvote_or_unvote_resource(self):
        upvote_url = f"/api/resources/{self.resource.pk}/upvote/"

        upvote_response = self.client.post(upvote_url, {}, format="json")
        unvote_response = self.client.delete(upvote_url)

        self.assertEqual(upvote_response.status_code, 401)
        self.assertEqual(unvote_response.status_code, 401)

    def test_resource_view_tracking_records_backend_event_and_ignores_payload_counts(self):
        self.client.force_authenticate(user=self.user)
        view_url = f"/api/resources/{self.resource.pk}/view/"

        response = self.client.post(view_url, {"view_count": 999}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["views"], 1)
        event = ResourceView.objects.get(resource=self.resource)
        self.assertEqual(event.user, self.user)
        self.assertNotIn("view_count", response.data)

    def test_resource_download_tracking_records_backend_event_and_ignores_payload_counts(self):
        self.client.force_authenticate(user=self.user)
        download_url = f"/api/resources/{self.resource.pk}/download/"

        response = self.client.post(download_url, {"download_count": 999}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["downloads"], 1)
        event = ResourceDownload.objects.get(resource=self.resource)
        self.assertEqual(event.user, self.user)
        self.assertNotIn("download_count", response.data)

    def test_tracking_cannot_access_hidden_resource_by_anonymous_or_other_user(self):
        hidden_resource = Resource.objects.create(
            title="Hidden tracking resource",
            uploader=self.user,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.DRAFT,
        )
        view_url = f"/api/resources/{hidden_resource.pk}/view/"
        download_url = f"/api/resources/{hidden_resource.pk}/download/"

        self.assertEqual(self.client.post(view_url, {}, format="json").status_code, 404)
        self.assertEqual(self.client.post(download_url, {}, format="json").status_code, 404)

        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(self.client.post(view_url, {}, format="json").status_code, 404)
        self.assertEqual(self.client.post(download_url, {}, format="json").status_code, 404)

        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post(view_url, {}, format="json").status_code, 201)
        self.assertEqual(self.client.post(download_url, {}, format="json").status_code, 201)

    def test_resource_crud_cannot_set_view_or_download_counts(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/resources/",
            {
                "title": "Counters ignored",
                "subject": "Physics",
                "resource_type": "notes",
                "view_count": 500,
                "download_count": 500,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        created_resource = Resource.objects.get(pk=response.data["id"])
        self.assertFalse(ResourceView.objects.filter(resource=created_resource).exists())
        self.assertFalse(ResourceDownload.objects.filter(resource=created_resource).exists())
        self.assertNotIn("view_count", response.data)
        self.assertNotIn("download_count", response.data)

    def test_non_owner_cannot_delete_resource(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(f"/api/resources/{self.resource.pk}/")

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_delete_resource(self):
        response = self.client.delete(f"/api/resources/{self.resource.pk}/")

        self.assertEqual(response.status_code, 401)

    def test_resource_create_rejects_invalid_link_payload(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/resources/",
            {"title": "Missing link URL", "subject": "Physics", "resource_type": "link"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("external_url", response.data)

    def test_resource_create_rejects_missing_required_and_invalid_fields(self):
        self.client.force_authenticate(user=self.user)
        invalid_payloads = (
            (
                "missing title",
                {"subject": "Physics", "resource_type": Resource.ResourceType.NOTES},
                "title",
            ),
            (
                "missing subject",
                {"title": "Missing subject", "resource_type": Resource.ResourceType.NOTES},
                "subject",
            ),
            (
                "invalid resource type",
                {"title": "Invalid type", "subject": "Physics", "resource_type": "invalid"},
                "resource_type",
            ),
            (
                "invalid difficulty",
                {
                    "title": "Invalid difficulty",
                    "subject": "Physics",
                    "resource_type": Resource.ResourceType.NOTES,
                    "difficulty": "impossible",
                },
                "difficulty",
            ),
        )

        for name, payload, field in invalid_payloads:
            with self.subTest(name=name):
                response = self.client.post("/api/resources/", payload, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_answer_creation_uses_question_and_request_author(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            f"/api/questions/{self.question.pk}/answers/", {"body": "Created answer"}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["question"], self.question.pk)
        self.assertEqual(response.data["author"]["username"], "api-peer")

    def test_answer_creation_notifies_question_author(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            f"/api/questions/{self.question.pk}/answers/", {"body": "Notify the question author"}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        notification = Notification.objects.get(
            recipient=self.user,
            notification_type=Notification.NotificationType.QUESTION_ANSWERED,
            payload__answer_id=response.data["id"],
        )
        self.assertEqual(notification.actor, self.other_user)
        self.assertEqual(notification.content_object, self.question)

    def test_self_answer_does_not_create_question_author_notification(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            f"/api/questions/{self.question.pk}/answers/", {"body": "Answering my own question"}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.user,
                notification_type=Notification.NotificationType.QUESTION_ANSWERED,
            ).exists()
        )

    @patch("apps.community.views.create_notification")
    def test_answer_creation_succeeds_when_notification_creation_fails(self, create_notification_mock):
        create_notification_mock.side_effect = RuntimeError("notification service unavailable")
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            f"/api/questions/{self.question.pk}/answers/", {"body": "Answer despite notification failure"}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Answer.objects.filter(pk=response.data["id"], question=self.question, author=self.other_user).exists())
        create_notification_mock.assert_called_once()

    def test_question_list_is_paginated_and_serializes_counts(self):
        response = self.client.get("/api/questions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual(response.data["results"][0]["id"], self.question.pk)
        self.assertEqual(response.data["results"][0]["answers"], 1)
        self.assertEqual(response.data["results"][0]["upvotes"], 0)

    def test_question_answers_are_paginated_serialized_and_scoped(self):
        second_answer = Answer.objects.create(
            question=self.question, author=self.other_user, body="Second API answer"
        )
        other_question = Question.objects.create(
            title="Other API question", body="Other question body", author=self.user, subject="Physics"
        )
        other_answer = Answer.objects.create(
            question=other_question, author=self.other_user, body="Answer for another question"
        )
        AnswerUpvote.objects.create(user=self.user, answer=second_answer)

        response = self.client.get(f"/api/questions/{self.question.pk}/answers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        answer_ids = {answer["id"] for answer in response.data["results"]}
        self.assertEqual(answer_ids, {self.answer.pk, second_answer.pk})
        self.assertNotIn(other_answer.pk, answer_ids)
        answer_data = next(answer for answer in response.data["results"] if answer["id"] == second_answer.pk)
        self.assertEqual(
            set(answer_data),
            {"id", "question", "author", "body", "is_helpful", "upvotes", "status", "created_at", "updated_at"},
        )
        self.assertEqual(answer_data["question"], self.question.pk)
        self.assertEqual(answer_data["author"]["username"], self.other_user.username)
        self.assertEqual(answer_data["body"], "Second API answer")
        self.assertEqual(answer_data["upvotes"], 1)

    def test_question_answers_return_empty_results_for_question_without_answers(self):
        question = Question.objects.create(
            title="Unanswered API question", body="No answers yet", author=self.user, subject="Physics"
        )

        response = self.client.get(f"/api/questions/{question.pk}/answers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_question_answers_follow_existing_public_visibility_rules(self):
        public_response = self.client.get(f"/api/questions/{self.question.pk}/answers/")
        self.assertEqual(public_response.status_code, 200)

        draft_question = Question.objects.create(
            title="Private API question for answers",
            body="Private question body",
            author=self.user,
            subject="Physics",
            status=PublicationStatus.DRAFT,
        )
        Answer.objects.create(
            question=draft_question,
            author=self.user,
            body="Private answer",
            status=PublicationStatus.DRAFT,
        )

        self.assertEqual(self.client.get(f"/api/questions/{draft_question.pk}/answers/").status_code, 404)

        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(self.client.get(f"/api/questions/{draft_question.pk}/answers/").status_code, 404)

        self.client.force_authenticate(user=self.user)
        owner_response = self.client.get(f"/api/questions/{draft_question.pk}/answers/")
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response.data["count"], 1)

    def test_question_can_be_created_and_detail_is_retrievable_by_slug(self):
        self.client.force_authenticate(user=self.other_user)
        create_response = self.client.post(
            "/api/questions/",
            {
                "title": "Created API question",
                "body": "A question created through the API.",
                "subject": "Chemistry",
                "author": self.user.pk,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["author"]["username"], "api-peer")
        self.assertNotEqual(create_response.data["slug"], "")

        detail_response = self.client.get(f"/api/questions/{create_response.data['slug']}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["id"], create_response.data["id"])

    def test_question_and_answer_creation_reject_invalid_input(self):
        self.client.force_authenticate(user=self.user)
        invalid_question = self.client.post(
            "/api/questions/", {"title": "Missing body", "subject": "Physics"}, format="json"
        )
        invalid_answer = self.client.post(
            f"/api/questions/{self.question.pk}/answers/", {"body": ""}, format="json"
        )

        self.assertEqual(invalid_question.status_code, 400)
        self.assertIn("body", invalid_question.data)
        self.assertEqual(invalid_answer.status_code, 400)
        self.assertIn("body", invalid_answer.data)

    def test_answer_creation_returns_not_found_for_nonexistent_question(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/questions/999999/answers/", {"body": "No question"}, format="json")

        self.assertEqual(response.status_code, 404)

    def test_missing_question_and_answer_targets_return_not_found(self):
        self.client.force_authenticate(user=self.user)

        missing_question_detail = self.client.get("/api/questions/does-not-exist/")
        missing_question_upvote = self.client.post("/api/questions/999999/upvote/", {}, format="json")
        missing_answer_detail = self.client.get(
            f"/api/questions/{self.question.pk}/answers/999999/"
        )
        missing_answer_upvote = self.client.post(
            f"/api/questions/{self.question.pk}/answers/999999/upvote/", {}, format="json"
        )

        self.assertEqual(missing_question_detail.status_code, 404)
        self.assertEqual(missing_question_upvote.status_code, 404)
        self.assertEqual(missing_answer_detail.status_code, 404)
        self.assertEqual(missing_answer_upvote.status_code, 404)

    def test_unauthenticated_users_cannot_create_questions_or_answers(self):
        question_response = self.client.post(
            "/api/questions/",
            {"title": "Anonymous question", "body": "Body", "subject": "Physics"},
            format="json",
        )
        answer_response = self.client.post(
            f"/api/questions/{self.question.pk}/answers/", {"body": "Anonymous answer"}, format="json"
        )

        self.assertEqual(question_response.status_code, 401)
        self.assertEqual(answer_response.status_code, 401)

    def test_question_upvotes_are_idempotent_and_user_scoped(self):
        upvote_url = f"/api/questions/{self.question.pk}/upvote/"
        self.client.force_authenticate(user=self.user)

        first_response = self.client.post(upvote_url, {}, format="json")
        duplicate_response = self.client.post(upvote_url, {}, format="json")

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(first_response.data["upvotes"], 1)
        self.assertEqual(QuestionUpvote.objects.filter(question=self.question).count(), 1)

        self.client.force_authenticate(user=self.other_user)
        other_response = self.client.post(upvote_url, {}, format="json")
        self.assertEqual(other_response.status_code, 201)
        self.assertEqual(other_response.data["upvotes"], 2)

    def test_question_upvote_delete_removes_only_own_vote_and_is_idempotent(self):
        QuestionUpvote.objects.create(user=self.user, question=self.question)
        QuestionUpvote.objects.create(user=self.other_user, question=self.question)
        upvote_url = f"/api/questions/{self.question.pk}/upvote/"
        self.client.force_authenticate(user=self.user)

        first_response = self.client.delete(upvote_url)
        repeated_response = self.client.delete(upvote_url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.data["upvotes"], 1)
        self.assertEqual(repeated_response.data["upvotes"], 1)
        self.assertFalse(QuestionUpvote.objects.filter(user=self.user, question=self.question).exists())
        self.assertTrue(QuestionUpvote.objects.filter(user=self.other_user, question=self.question).exists())

    def test_answer_upvotes_support_idempotent_add_remove_and_object_isolation(self):
        upvote_url = f"/api/questions/{self.question.pk}/answers/{self.answer.pk}/upvote/"
        wrong_question = Question.objects.create(
            title="Other question", body="Other body", author=self.user, subject="Physics"
        )
        self.client.force_authenticate(user=self.user)

        first_response = self.client.post(upvote_url, {}, format="json")
        duplicate_response = self.client.post(upvote_url, {}, format="json")
        wrong_object_response = self.client.post(
            f"/api/questions/{wrong_question.pk}/answers/{self.answer.pk}/upvote/", {}, format="json"
        )
        delete_response = self.client.delete(upvote_url)
        repeated_delete_response = self.client.delete(upvote_url)

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(first_response.data["upvotes"], 1)
        self.assertEqual(wrong_object_response.status_code, 404)
        self.assertEqual(delete_response.data["upvotes"], 0)
        self.assertEqual(repeated_delete_response.data["upvotes"], 0)
        self.assertFalse(AnswerUpvote.objects.filter(answer=self.answer).exists())

    def test_unauthenticated_users_cannot_vote_on_questions_or_answers(self):
        question_response = self.client.post(f"/api/questions/{self.question.pk}/upvote/", {}, format="json")
        answer_response = self.client.post(
            f"/api/questions/{self.question.pk}/answers/{self.answer.pk}/upvote/", {}, format="json"
        )

        self.assertEqual(question_response.status_code, 401)
        self.assertEqual(answer_response.status_code, 401)

    def test_question_author_can_update_and_delete_question(self):
        self.client.force_authenticate(user=self.user)

        put_response = self.client.put(
            f"/api/questions/{self.question.slug}/",
            {"title": "Replaced question", "body": "Updated body", "subject": "Physics"},
            format="json",
        )
        patch_response = self.client.patch(
            f"/api/questions/{self.question.slug}/", {"title": "Patched question"}, format="json"
        )
        delete_response = self.client.delete(f"/api/questions/{self.question.slug}/")

        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(delete_response.status_code, 204)

    def test_question_non_owner_cannot_update_or_delete_question(self):
        self.client.force_authenticate(user=self.other_user)

        patch_response = self.client.patch(
            f"/api/questions/{self.question.slug}/", {"title": "Not allowed"}, format="json"
        )
        put_response = self.client.put(
            f"/api/questions/{self.question.slug}/",
            {"title": "Not allowed", "body": "Body", "subject": "Physics"},
            format="json",
        )
        delete_response = self.client.delete(f"/api/questions/{self.question.slug}/")

        self.assertEqual(patch_response.status_code, 403)
        self.assertEqual(put_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

    def test_anonymous_question_mutation_requires_authentication(self):
        response = self.client.patch(
            f"/api/questions/{self.question.slug}/", {"title": "Unauthenticated"}, format="json"
        )

        self.assertEqual(response.status_code, 401)

    def test_answer_author_can_update_and_delete_answer(self):
        self.client.force_authenticate(user=self.user)
        answer_url = f"/api/questions/{self.question.pk}/answers/{self.answer.pk}/"

        put_response = self.client.put(answer_url, {"body": "Replaced answer"}, format="json")
        patch_response = self.client.patch(answer_url, {"body": "Patched answer"}, format="json")
        delete_response = self.client.delete(answer_url)

        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(delete_response.status_code, 204)

    def test_answer_non_owner_cannot_update_or_delete_answer(self):
        self.client.force_authenticate(user=self.other_user)
        answer_url = f"/api/questions/{self.question.pk}/answers/{self.answer.pk}/"

        patch_response = self.client.patch(answer_url, {"body": "Not allowed"}, format="json")
        put_response = self.client.put(answer_url, {"body": "Not allowed"}, format="json")
        delete_response = self.client.delete(answer_url)

        self.assertEqual(patch_response.status_code, 403)
        self.assertEqual(put_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

    def test_anonymous_answer_mutation_requires_authentication(self):
        answer_url = f"/api/questions/{self.question.pk}/answers/{self.answer.pk}/"

        response = self.client.patch(answer_url, {"body": "Unauthenticated"}, format="json")

        self.assertEqual(response.status_code, 401)

    def test_notifications_are_scoped_to_authenticated_recipient(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f"/api/notifications/?user_id={self.other_user.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["recipient"]["username"], "api-user")

    def test_notification_list_returns_newest_authenticated_users_notifications(self):
        older = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
            payload={"position": "older"},
        )
        newest = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
            payload={"position": "newest"},
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/notifications/")

        self.assertEqual(response.status_code, 200)
        result_ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(result_ids[:2], [newest.pk, older.pk])

    def test_notification_list_is_paginated(self):
        notifications = [
            Notification.objects.create(
                recipient=self.user,
                actor=self.other_user,
                notification_type=Notification.NotificationType.SYSTEM,
                payload={"position": index},
            )
            for index in range(StudyMatePagination.page_size + 1)
        ]
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual(response.data["count"], len(notifications) + 1)
        self.assertEqual(len(response.data["results"]), StudyMatePagination.page_size)
        self.assertIsNotNone(response.data["next"])

    def test_authenticated_user_can_mark_one_notification_read(self):
        notification = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/notifications/{notification.pk}/read/",
            {"recipient": self.other_user.pk, "is_read": False},
            format="json",
        )

        notification.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_read"])
        self.assertTrue(notification.is_read)

    def test_authenticated_user_can_mark_all_own_unread_notifications_read(self):
        unread_notifications = [
            Notification.objects.create(
                recipient=self.user,
                actor=self.other_user,
                notification_type=Notification.NotificationType.SYSTEM,
            )
            for _ in range(2)
        ]
        already_read = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
            is_read=True,
        )
        other_user_notification = Notification.objects.create(
            recipient=self.other_user,
            actor=self.user,
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            "/api/notifications/read-all/",
            {"recipient": self.other_user.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"updated": len(unread_notifications) + 1})
        self.assertTrue(all(Notification.objects.get(pk=item.pk).is_read for item in unread_notifications))
        self.assertTrue(Notification.objects.get(pk=already_read.pk).is_read)
        self.assertFalse(Notification.objects.get(pk=other_user_notification.pk).is_read)

    def test_repeated_notification_read_operations_are_safe(self):
        notification = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.client.force_authenticate(user=self.user)

        first_read = self.client.patch(f"/api/notifications/{notification.pk}/read/", {}, format="json")
        repeated_read = self.client.patch(f"/api/notifications/{notification.pk}/read/", {}, format="json")
        first_all = self.client.patch("/api/notifications/read-all/", {}, format="json")
        repeated_all = self.client.patch("/api/notifications/read-all/", {}, format="json")

        self.assertEqual(first_read.status_code, 200)
        self.assertEqual(repeated_read.status_code, 200)
        self.assertEqual(first_all.status_code, 200)
        self.assertEqual(repeated_all.status_code, 200)
        self.assertEqual(repeated_all.data, {"updated": 0})

    def test_another_users_notification_id_is_not_accessible(self):
        notification = Notification.objects.create(
            recipient=self.other_user,
            actor=self.user,
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(f"/api/notifications/{notification.pk}/read/", {}, format="json")

        notification.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertFalse(notification.is_read)

    def test_notification_detail_is_private_to_recipient(self):
        own_notification = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
        )
        other_notification = Notification.objects.create(
            recipient=self.other_user,
            actor=self.user,
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.client.force_authenticate(user=self.user)

        own_response = self.client.get(f"/api/notifications/{own_notification.pk}/")
        other_response = self.client.get(f"/api/notifications/{other_notification.pk}/")

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(own_response.data["id"], own_notification.pk)
        self.assertEqual(other_response.status_code, 404)

    def test_access_token_cookie_authenticates_protected_api(self):
        access_token = RefreshToken.for_user(self.user).access_token
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(access_token)

        response = self.client.get("/api/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(settings.JWT_ACCESS_COOKIE_HTTPONLY)
        self.assertTrue(settings.JWT_REFRESH_COOKIE_HTTPONLY)
        self.assertEqual(response.data["results"][0]["recipient"]["username"], "api-user")

    def test_invalid_or_expired_access_cookie_cannot_authenticate_me(self):
        expired_access = AccessToken.for_user(self.user)
        expired_access["exp"] = 0

        for raw_token in ("not-a-valid-access-token", str(expired_access)):
            with self.subTest(token=raw_token):
                self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = raw_token
                response = self.client.get("/api/auth/me/")

                self.assertEqual(response.status_code, 401)

    def test_cookie_jwt_requires_csrf_for_unsafe_requests(self):
        access_token = RefreshToken.for_user(self.user).access_token
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(access_token)

        response = csrf_client.post(
            "/api/resources/",
            {"title": "Cookie-authored notes", "subject": "Physics", "resource_type": "notes"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_resource_mutation_is_limited_to_owner(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            f"/api/resources/{self.resource.pk}/", {"title": "Not allowed"}, format="json"
        )
        put_response = self.client.put(
            f"/api/resources/{self.resource.pk}/",
            {"title": "Not allowed", "subject": "Physics", "resource_type": "notes"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(put_response.status_code, 403)

    def test_protected_writes_require_authentication(self):
        response = self.client.post(
            "/api/resources/",
            {"title": "Unauthenticated notes", "subject": "Physics", "resource_type": "notes"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_owned_object_mutation_returns_401(self):
        response = self.client.patch(
            f"/api/resources/{self.resource.pk}/", {"title": "Unauthenticated update"}, format="json"
        )

        self.assertEqual(response.status_code, 401)

    def test_notifications_require_authentication(self):
        response = self.client.get("/api/notifications/")

        self.assertEqual(response.status_code, 401)

    def test_notification_read_operations_require_authentication(self):
        notification = Notification.objects.create(
            recipient=self.user,
            actor=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
        )

        read_response = self.client.patch(f"/api/notifications/{notification.pk}/read/", {}, format="json")
        read_all_response = self.client.patch("/api/notifications/read-all/", {}, format="json")

        self.assertEqual(read_response.status_code, 401)
        self.assertEqual(read_all_response.status_code, 401)

    def test_missing_resource_is_not_found_and_unsupported_methods_are_rejected(self):
        missing_response = self.client.get("/api/resources/does-not-exist/")
        video_delete_response = self.client.delete(f"/api/videos/{self.video.slug}/")
        question_patch_response = self.client.patch(
            f"/api/questions/{self.question.slug}/", {"title": "Unauthenticated"}, format="json"
        )

        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(video_delete_response.status_code, 405)
        self.assertEqual(question_patch_response.status_code, 401)
