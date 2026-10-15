from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.education.models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest
from apps.users.models import StudentProfile


User = get_user_model()


class EducationProfileAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="education-owner",
            email="education-owner@example.com",
            password="not-used-in-test",
        )
        cls.other_user = User.objects.create_user(
            username="education-peer",
            email="education-peer@example.com",
            password="not-used-in-test",
        )
        cls.engineering = EducationBackground.objects.create(
            name="Engineering", slug="test-engineering"
        )
        cls.school = EducationBackground.objects.create(name="School", slug="test-school")
        cls.other = EducationBackground.objects.get(slug="other")
        cls.commerce = EducationBackground.objects.create(
            name="Commerce", slug="test-commerce"
        )

        cls.btech = Course.objects.create(
            education_background=cls.engineering, name="BTech", slug="test-btech"
        )
        cls.school_course = Course.objects.create(
            education_background=cls.school,
            name="Class-based Education",
            slug="test-school-class",
        )
        cls.other_course = Course.objects.get(
            education_background=cls.other, slug="other"
        )
        cls.bcom = Course.objects.create(
            education_background=cls.commerce, name="BCom", slug="test-bcom"
        )

        cls.semester = AcademicLevel.objects.create(
            course=cls.btech,
            name="7th Semester",
            slug="test-semester-7",
            level_type=AcademicLevel.LevelType.SEMESTER,
            order=7,
        )
        cls.school_class = AcademicLevel.objects.create(
            course=cls.school_course,
            name="Class 10",
            slug="test-class-10",
            level_type=AcademicLevel.LevelType.CLASS,
            order=10,
        )
        cls.year = AcademicLevel.objects.create(
            course=cls.bcom,
            name="2nd Year",
            slug="test-year-2",
            level_type=AcademicLevel.LevelType.YEAR,
            order=2,
        )

    def setUp(self):
        self.client = APIClient()

    def onboarding(self, **overrides):
        payload = {
            "education_background": self.engineering.pk,
            "course": self.btech.pk,
            "academic_level": self.semester.pk,
            "country": "India",
            "state": "Delhi",
            "city": "New Delhi",
        }
        payload.update(overrides)
        return payload

    def test_valid_onboarding_persists_location_semester_and_without_interests(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post("/api/users/onboarding/", self.onboarding(), format="json")

        self.assertEqual(response.status_code, 200, response.data)
        profile = StudentProfile.objects.get(user=self.user)
        self.assertTrue(profile.onboarding_completed)
        self.assertEqual(profile.country, "India")
        self.assertEqual(profile.state, "Delhi")
        self.assertEqual(profile.city, "New Delhi")
        self.assertEqual(profile.academic_level_type, "semester")
        self.assertEqual(profile.academic_level_value, "7th Semester")
        self.assertFalse(profile.student_interests.exists())
        self.assertEqual(response.data["profile"]["academic_level_type"], "semester")

    def test_other_background_and_other_course_accept_custom_values(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding(
                education_background=self.other.pk,
                custom_background="Independent Creative Technology",
                course=self.other_course.pk,
                custom_course="Creative coding programme",
                academic_level=None,
                academic_level_type="stage",
                academic_level_value="Portfolio stage",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        profile = StudentProfile.objects.get(user=self.user)
        self.assertEqual(profile.course_id, self.other_course.pk)
        self.assertEqual(profile.education_background_id, self.other.pk)
        self.assertEqual(profile.custom_background, "Independent Creative Technology")
        self.assertEqual(profile.custom_course, "Creative coding programme")
        self.assertEqual(profile.academic_level_type, "stage")
        self.assertEqual(profile.academic_level_value, "Portfolio stage")
        self.assertTrue(profile.onboarding_completed)

    def test_school_class_flow_and_year_flow_are_supported(self):
        self.client.force_authenticate(user=self.user)

        school_response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding(
                education_background=self.school.pk,
                course=self.school_course.pk,
                academic_level=self.school_class.pk,
            ),
            format="json",
        )
        self.assertEqual(school_response.status_code, 200, school_response.data)
        profile = StudentProfile.objects.get(user=self.user)
        self.assertEqual(profile.academic_level_type, "class")
        self.assertEqual(profile.academic_level_value, "Class 10")

        self.client.force_authenticate(user=self.other_user)
        year_response = self.client.post(
            "/api/users/onboarding/",
            self.onboarding(
                education_background=self.bcom.education_background_id,
                course=self.bcom.pk,
                academic_level=self.year.pk,
            ),
            format="json",
        )
        self.assertEqual(year_response.status_code, 200, year_response.data)
        other_profile = StudentProfile.objects.get(user=self.other_user)
        self.assertEqual(other_profile.academic_level_type, "year")
        self.assertEqual(other_profile.academic_level_value, "2nd Year")

    def test_profile_update_persists_location_and_custom_education(self):
        self.client.force_authenticate(user=self.user)
        self.client.post("/api/users/onboarding/", self.onboarding(), format="json")

        response = self.client.patch(
            f"/api/users/{self.user.username}/",
            {
                "country": "India",
                "state": "Maharashtra",
                "city": "Pune",
                "education_background": self.other.pk,
                "custom_background": "Design technology",
                "course": self.other_course.pk,
                "custom_course": "UX Research",
                "academic_level": None,
                "academic_level_type": "other",
                "academic_level_value": "Professional portfolio stage",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        profile = StudentProfile.objects.get(user=self.user)
        self.assertEqual((profile.country, profile.state, profile.city), ("India", "Maharashtra", "Pune"))
        self.assertEqual(profile.custom_background, "Design technology")
        self.assertEqual(profile.custom_course, "UX Research")
        self.assertEqual(profile.academic_level_type, "other")
        self.assertTrue(profile.onboarding_completed)

    def test_profile_update_persists_course_compatible_interests(self):
        interest = Interest.objects.create(
            name="Distributed Systems",
            slug="test-distributed-systems",
        )
        interest.courses.add(self.btech)
        self.client.force_authenticate(user=self.user)
        self.client.post("/api/users/onboarding/", self.onboarding(), format="json")

        response = self.client.patch(
            f"/api/users/{self.user.username}/",
            {"interest_ids": [interest.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            list(
                StudentInterest.objects.filter(student_profile__user=self.user).values_list(
                    "interest_id", flat=True
                )
            ),
            [interest.pk],
        )
        self.assertEqual(response.data["interests"][0]["id"], interest.pk)

        reopened = self.client.get(f"/api/users/{self.user.username}/")

        self.assertEqual(reopened.status_code, 200, reopened.data)
        self.assertEqual([item["id"] for item in reopened.data["interests"]], [interest.pk])

    def test_profile_update_rejects_interest_from_another_course(self):
        interest = Interest.objects.create(
            name="Accounting",
            slug="test-accounting",
        )
        interest.courses.add(self.bcom)
        self.client.force_authenticate(user=self.user)
        self.client.post("/api/users/onboarding/", self.onboarding(), format="json")

        response = self.client.patch(
            f"/api/users/{self.user.username}/",
            {"interest_ids": [interest.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("interest_ids", response.data)
        self.assertFalse(StudentInterest.objects.filter(student_profile__user=self.user).exists())

    def test_profile_list_reuses_prefetched_interests(self):
        interest = Interest.objects.create(
            name="Networks",
            slug="test-networks",
        )
        interest.courses.add(self.btech)
        first_profile = StudentProfile.objects.create(user=self.user, course=self.btech)
        StudentInterest.objects.create(student_profile=first_profile, interest=interest)

        with CaptureQueriesContext(connection) as one_profile_queries:
            first_response = self.client.get("/api/users/")

        self.assertEqual(first_response.status_code, 200)
        for index in range(2):
            extra_user = User.objects.create_user(
                username=f"education-extra-{index}",
                email=f"education-extra-{index}@example.com",
                password="not-used-in-test",
            )
            extra_profile = StudentProfile.objects.create(user=extra_user, course=self.btech)
            StudentInterest.objects.create(student_profile=extra_profile, interest=interest)

        with CaptureQueriesContext(connection) as several_profile_queries:
            response = self.client.get("/api/users/")

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(several_profile_queries),
            len(one_profile_queries) + 1,
            "Profile interests should be served by the prefetch query, not one query per profile.",
        )

    def test_invalid_relationship_and_unauthorized_profile_update_are_rejected(self):
        self.client.force_authenticate(user=self.user)
        invalid = self.client.post(
            "/api/users/onboarding/",
            self.onboarding(
                education_background=self.engineering.pk,
                course=self.school_course.pk,
                academic_level=self.school_class.pk,
            ),
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("course", invalid.data)

        self.client.force_authenticate(user=self.other_user)
        forbidden = self.client.patch(
            f"/api/users/{self.user.username}/",
            {"city": "Should not persist"},
            format="json",
        )
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_authenticate(user=None)
        unauthenticated = self.client.post(
            "/api/users/onboarding/", self.onboarding(), format="json"
        )
        self.assertEqual(unauthenticated.status_code, 401)

    def test_levels_can_be_filtered_by_course_and_background_relationship(self):
        correct = self.client.get(
            "/api/education/levels/",
            {"course": self.btech.pk, "background": self.engineering.pk},
        )
        wrong = self.client.get(
            "/api/education/levels/",
            {"course": self.btech.pk, "background": self.school.pk},
        )

        self.assertEqual(correct.status_code, 200)
        self.assertEqual([item["id"] for item in correct.data["results"]], [self.semester.pk])
        self.assertEqual(wrong.status_code, 200)
        self.assertEqual(wrong.data["results"], [])
