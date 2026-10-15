from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.community.models import DiscussionComment, DiscussionCommentLike
from apps.education.models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest
from apps.interactions.models import ResourceRating, ResourceUpvote, SavedResource
from apps.users.models import StudentProfile

from .models import PublicationStatus, Resource, ResourceDownload, ResourceView


class SubjectRecommendationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="subject-student", password="not-used-in-test")
        cls.peer = User.objects.create_user(username="subject-peer", password="not-used-in-test")
        cls.engineering = EducationBackground.objects.create(name="Engineering", slug="test-engineering")
        cls.commerce = EducationBackground.objects.create(name="Commerce", slug="test-commerce")
        cls.btech = Course.objects.create(education_background=cls.engineering, name="B.Tech CSE", slug="test-btech-cse")
        cls.bcom = Course.objects.create(education_background=cls.commerce, name="B.Com", slug="test-bcom")
        cls.btech_level = AcademicLevel.objects.create(
            course=cls.btech,
            name="1st Semester",
            slug="test-btech-semester-1",
            level_type=AcademicLevel.LevelType.SEMESTER,
            order=1,
        )
        cls.bcom_level = AcademicLevel.objects.create(
            course=cls.bcom,
            name="1st Year",
            slug="test-bcom-year-1",
            level_type=AcademicLevel.LevelType.YEAR,
            order=1,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.profile = StudentProfile.objects.create(
            user=self.user,
            education_background=self.engineering,
            course=self.btech,
            academic_level=self.btech_level,
            onboarding_completed=True,
        )

    def create_resource(self, subject, *, academic_level=None):
        return Resource.objects.create(
            title=f"{subject} notes",
            uploader=self.user,
            subject=subject,
            academic_level=academic_level,
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )

    def test_recommendations_combine_academic_interest_and_real_engagement(self):
        data_structures = self.create_resource("Data Structures", academic_level=self.btech_level)
        self.create_resource("AI/ML", academic_level=self.btech_level)
        ai_interest = Interest.objects.create(name="AI/ML", slug="test-ai-ml")
        ai_interest.courses.add(self.btech)
        StudentInterest.objects.create(student_profile=self.profile, interest=ai_interest)

        ResourceView.objects.create(resource=data_structures, user=self.peer)
        ResourceDownload.objects.create(resource=data_structures, user=self.peer)
        SavedResource.objects.create(resource=data_structures, user=self.peer)
        ResourceUpvote.objects.create(resource=data_structures, user=self.peer)
        ResourceRating.objects.create(resource=data_structures, user=self.peer, rating=5)
        comment = DiscussionComment.objects.create(resource=data_structures, author=self.peer, body="Helpful")
        DiscussionCommentLike.objects.create(comment=comment, user=self.user)

        response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 200)
        subjects = response.data["results"]
        by_name = {subject["name"]: subject for subject in subjects}
        self.assertIn("Data Structures", by_name)
        self.assertIn("AI/ML", by_name)
        self.assertGreaterEqual(by_name["Data Structures"]["engagement_count"], 7)
        self.assertTrue(by_name["Data Structures"]["is_trending"])
        self.assertTrue(by_name["AI/ML"]["is_personalized"])

    def test_course_change_prioritizes_the_new_course_without_fixed_mappings(self):
        accounting_interest = Interest.objects.create(name="Accounting", slug="test-accounting")
        accounting_interest.courses.add(self.bcom)
        StudentInterest.objects.create(student_profile=self.profile, interest=accounting_interest)
        self.profile.education_background = self.commerce
        self.profile.course = self.bcom
        self.profile.academic_level = self.bcom_level
        self.profile.save(update_fields=["education_background", "course", "academic_level"])
        self.create_resource("Accounting", academic_level=self.bcom_level)

        response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 200)
        accounting = next(subject for subject in response.data["results"] if subject["name"] == "Accounting")
        self.assertTrue(accounting["is_personalized"])

    def test_incomplete_profile_uses_general_subjects_and_zero_engagement_is_safe(self):
        self.profile.onboarding_completed = False
        self.profile.save(update_fields=["onboarding_completed"])
        new_subject = self.create_resource("General Mathematics")
        course_interest = Interest.objects.create(name="Study Skills", slug="test-study-skills")
        course_interest.courses.add(self.btech)

        response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["profile_complete"])
        subjects = {subject["name"]: subject for subject in response.data["results"]}
        self.assertIn("General Mathematics", subjects)
        self.assertGreaterEqual(subjects["General Mathematics"]["content_count"], 1)
        self.assertEqual(subjects["General Mathematics"]["engagement_count"], 0)
        self.assertNotIn("Study Skills", subjects)
        self.assertNotEqual(new_subject.subject, "")

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 401)
