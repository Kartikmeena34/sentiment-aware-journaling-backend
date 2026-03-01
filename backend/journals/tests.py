from django.test import TestCase

# Create your tests here.
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from unittest.mock import patch


class FullBackendIntegrationTest(APITestCase):

    def setUp(self):
        self.username = "testuser"
        self.password = "testpass123"

    # -----------------------------
    # REGISTER TEST
    # -----------------------------
    def test_register_user(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": self.username, "password": self.password},
            format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username=self.username).exists())

    # -----------------------------
    # LOGIN TEST
    # -----------------------------
    def test_login_returns_tokens(self):
        User.objects.create_user(
            username=self.username,
            password=self.password
        )

        response = self.client.post(
            "/api/auth/login/",
            {"username": self.username, "password": self.password},
            format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    # -----------------------------
    # REFRESH TOKEN TEST
    # -----------------------------
    def test_refresh_token(self):
        User.objects.create_user(
            username=self.username,
            password=self.password
        )

        login = self.client.post(
            "/api/auth/login/",
            {"username": self.username, "password": self.password},
            format="json"
        )

        refresh_token = login.data["refresh"]

        response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": refresh_token},
            format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    # -----------------------------
    # JOURNAL REQUIRES AUTH
    # -----------------------------
    def test_journal_requires_auth(self):
        response = self.client.post(
            "/api/journal/create/",
            {"text": "Test without auth"},
            format="json"
        )
        self.assertEqual(response.status_code, 401)

    # -----------------------------
    # JOURNAL CREATION WITH AUTH
    # -----------------------------
    @patch("journals.views.detect_emotion")
    def test_create_journal_authenticated(self, mock_detect):
        mock_detect.return_value = {
            "dominant_emotion": "joy",
            "confidence": 0.9,
            "raw": {"joy": 0.9}
        }

        User.objects.create_user(
            username=self.username,
            password=self.password
        )

        login = self.client.post(
            "/api/auth/login/",
            {"username": self.username, "password": self.password},
            format="json"
        )

        access_token = login.data["access"]
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.post(
            "/api/journal/create/",
            {"text": "I feel happy"},
            format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("journal_id", response.data)
        self.assertIn("analytics", response.data)

    # -----------------------------
    # ANALYTICS STRUCTURE TEST
    # -----------------------------
    @patch("journals.views.detect_emotion")
    def test_analytics_structure(self, mock_detect):
        mock_detect.return_value = {
            "dominant_emotion": "neutral",
            "confidence": 0.8,
            "raw": {"neutral": 0.8}
        }

        User.objects.create_user(
            username=self.username,
            password=self.password
        )

        login = self.client.post(
            "/api/auth/login/",
            {"username": self.username, "password": self.password},
            format="json"
        )

        access_token = login.data["access"]
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        # create one journal entry
        self.client.post(
            "/api/journal/create/",
            {"text": "Testing analytics"},
            format="json"
        )

        response = self.client.get("/api/journal/analytics/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("weekly_distribution", response.data)
        self.assertIn("stability_score", response.data)
        self.assertIn("trends", response.data)