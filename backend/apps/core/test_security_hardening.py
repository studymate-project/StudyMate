from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.education.models import Interest, StudentInterest
from apps.users.models import StudentProfile


class StudentInterestPrivacyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="interest-owner",
            email="interest-owner@example.com",
            password="not-used-in-test",
        )
        self.other_user = user_model.objects.create_user(
            username="interest-other",
            email="interest-other@example.com",
            password="not-used-in-test",
        )
        owner_profile = StudentProfile.objects.create(user=self.owner)
        other_profile = StudentProfile.objects.create(user=self.other_user)
        interest = Interest.objects.create(name="Privacy", slug="privacy")
        StudentInterest.objects.create(student_profile=owner_profile, interest=interest)
        StudentInterest.objects.create(student_profile=other_profile, interest=interest)
        self.client = APIClient()

    def test_student_interests_require_authentication_and_are_user_scoped(self):
        self.assertEqual(self.client.get("/api/education/student-interests/").status_code, 401)

        self.client.force_authenticate(user=self.owner)
        own_response = self.client.get("/api/education/student-interests/")
        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(len(own_response.data["results"]), 1)
        self.assertEqual(
            own_response.data["results"][0]["student_profile"],
            StudentProfile.objects.get(user=self.owner).pk,
        )

        other_interest = StudentInterest.objects.get(student_profile__user=self.other_user)
        self.assertEqual(
            self.client.get(f"/api/education/student-interests/{other_interest.pk}/").status_code,
            404,
        )


class AuthenticationCSRFTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="csrf-user",
            email="csrf-user@example.com",
            password="not-used-in-test",
        )
        self.client = APIClient(enforce_csrf_checks=True)

    def test_login_requires_csrf_token_for_browser_style_requests(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "csrf-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
