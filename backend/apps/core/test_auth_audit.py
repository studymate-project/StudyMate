from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


User = get_user_model()


class BearerJWTAuthenticationAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="bearer-audit-user",
            email="bearer-audit-user@example.com",
            password="not-used-in-test",
        )
        self.client = APIClient()

    def test_valid_bearer_access_token_authenticates_me(self):
        access_token = RefreshToken.for_user(self.user).access_token

        response = self.client.get(
            "/api/auth/me/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], self.user.pk)

    def test_invalid_expired_and_refresh_bearer_tokens_are_rejected(self):
        expired_access = AccessToken.for_user(self.user)
        expired_access["exp"] = 0
        refresh_token = RefreshToken.for_user(self.user)

        for raw_token in ("not-a-token", str(expired_access), str(refresh_token)):
            with self.subTest(token_type="invalid or wrong JWT type"):
                response = self.client.get(
                    "/api/auth/me/",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

            self.assertEqual(response.status_code, 401)

