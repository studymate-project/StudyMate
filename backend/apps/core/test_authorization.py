from django.contrib.auth import get_user_model
from django.test import TestCase


User = get_user_model()


class AdminAuthorizationTests(TestCase):
    def setUp(self) -> None:
        self.student = User.objects.create_user(
            username="authorization-student",
            password="not-used-in-test",
        )
        self.admin = User.objects.create_superuser(
            username="authorization-admin",
            email="authorization-admin@example.com",
            password="not-used-in-test",
        )

    def test_admin_index_is_restricted_to_admin_users(self):
        self.client.force_login(self.student)
        student_response = self.client.get("/admin/")

        self.assertEqual(student_response.status_code, 302)
        self.assertIn("/admin/login/", student_response["Location"])

        self.client.force_login(self.admin)
        admin_response = self.client.get("/admin/")

        self.assertEqual(admin_response.status_code, 200)

    def test_search_namespace_does_not_duplicate_auth_routes(self):
        response = self.client.post(
            "/api/search/login/",
            {"email": "authorization-student@example.com", "password": "not-used-in-test"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
