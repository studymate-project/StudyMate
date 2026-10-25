from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.education.models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest
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

    def test_csrf_bootstrap_returns_token_for_cross_origin_clients(self):
        response = self.client.get("/api/auth/csrf/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["csrf_token"])
        self.assertIn("csrftoken", response.cookies)

        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "csrf-user@example.com", "password": "not-used-in-test"},
            format="json",
            HTTP_X_CSRFTOKEN=response.data["csrf_token"],
        )
        self.assertEqual(login_response.status_code, 200)

        refresh_response = self.client.post(
            "/api/auth/refresh/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=response.data["csrf_token"],
        )
        self.assertEqual(refresh_response.status_code, 200)

    def test_login_requires_csrf_token_for_browser_style_requests(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "csrf-user@example.com", "password": "not-used-in-test"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_refresh_without_a_cookie_is_unauthenticated_not_a_csrf_failure(self):
        response = self.client.post("/api/auth/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Invalid or expired refresh token.")

    def test_refresh_with_a_valid_cookie_still_requires_csrf(self):
        user = get_user_model().objects.get(email="csrf-user@example.com")
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = str(RefreshToken.for_user(user))

        response = self.client.post("/api/auth/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_refresh_with_an_expired_cookie_is_unauthenticated_before_csrf(self):
        user = get_user_model().objects.get(email="csrf-user@example.com")
        expired = RefreshToken.for_user(user)
        expired["exp"] = 0
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = str(expired)

        response = self.client.post("/api/auth/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 401)

    @override_settings(
        CORS_ALLOWED_ORIGINS=["https://studymate.vercel.app"],
        CSRF_TRUSTED_ORIGINS=["https://studymate.vercel.app"],
        CSRF_COOKIE_SECURE=True,
        CSRF_COOKIE_SAMESITE="None",
        JWT_COOKIE_SECURE=True,
        JWT_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
    )
    def test_cross_origin_browser_flow_bootstraps_csrf_for_account_and_profile_mutations(self):
        origin = "https://studymate.vercel.app"
        bootstrap = self.client.get("/api/auth/csrf/", HTTP_ORIGIN=origin)

        self.assertEqual(bootstrap.status_code, 200)
        self.assertEqual(bootstrap["Access-Control-Allow-Origin"], origin)
        self.assertEqual(bootstrap["Access-Control-Allow-Credentials"], "true")
        self.assertTrue(bootstrap.data["csrf_token"])
        csrf_cookie = bootstrap.cookies["csrftoken"]
        self.assertEqual(csrf_cookie["samesite"], "None")
        self.assertTrue(csrf_cookie["secure"])
        self.assertEqual(csrf_cookie["path"], "/")

        csrf_token = bootstrap.data["csrf_token"]
        with patch("apps.users.tasks.send_signup_verification_email_task.delay") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                signup = self.client.post(
                    "/api/auth/signup/",
                    {
                        "name": "Cross Origin Student",
                        "email": "cross-origin-student@example.com",
                        "password": "A-strong-cross-origin-password-42!",
                        "country": "India",
                        "state": "Delhi",
                        "city": "New Delhi",
                    },
                    format="json",
                    HTTP_ORIGIN=origin,
                    HTTP_X_CSRFTOKEN=csrf_token,
                )
        self.assertEqual(signup.status_code, 202, signup.data)
        enqueue.assert_called_once()
        verification_code = enqueue.call_args.args[1]
        username = get_user_model().objects.get(email="cross-origin-student@example.com").username

        verify = self.client.post(
            "/api/auth/signup/verification/verify/",
            {"email": "cross-origin-student@example.com", "code": verification_code},
            format="json",
            HTTP_ORIGIN=origin,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(verify.status_code, 200, verify.data)

        login = self.client.post(
            "/api/auth/login/",
            {"email": "cross-origin-student@example.com", "password": "A-strong-cross-origin-password-42!"},
            format="json",
            HTTP_ORIGIN=origin,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login.status_code, 200, login.data)

        background = EducationBackground.objects.get(slug="engineering")
        course = Course.objects.get(education_background=background, slug="btech")
        level = AcademicLevel.objects.filter(course=course).order_by("order").first()
        onboarding = self.client.post(
            "/api/users/onboarding/",
            {
                "education_background": background.pk,
                "course": course.pk,
                "academic_level": level.pk,
                "country": "India",
                "state": "Delhi",
                "city": "New Delhi",
            },
            format="json",
            HTTP_ORIGIN=origin,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(onboarding.status_code, 200, onboarding.data)

        profile_update = self.client.patch(
            f"/api/users/{username}/",
            {"city": "Pune"},
            format="json",
            HTTP_ORIGIN=origin,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(profile_update.status_code, 200, profile_update.data)

        logout = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_ORIGIN=origin,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(
            self.client.get("/api/auth/me/", HTTP_ORIGIN=origin).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/refresh/",
                {},
                format="json",
                HTTP_ORIGIN=origin,
                HTTP_X_CSRFTOKEN=csrf_token,
            ).status_code,
            401,
        )
