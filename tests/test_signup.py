import pytest
from django.contrib.auth.models import User
from unittest.mock import patch

SIGNUP_URL = "/accounts/signup/"

VALID_PAYLOAD = {
    "username": "newuser",
    "email": "newuser@test.com",
    "password": "pass1234",
    "password2": "pass1234",
}


@pytest.mark.django_db
class TestSignup:

    @patch("accounts.views.send_otp")
    def test_signup_success(self, mock_send, anon_client):
        """Valid signup creates an inactive user and returns 201 with OTP sent message."""
        res = anon_client.post(SIGNUP_URL, VALID_PAYLOAD)
        assert res.status_code == 201
        assert res.data["message"] == "Otp sent successfully"
        user = User.objects.get(email=VALID_PAYLOAD["email"])
        assert user.is_active is False

    @patch("accounts.views.send_otp")
    def test_signup_creates_otp(self, mock_send, anon_client):
        """Signup generates an unused signup OTP record linked to the new user."""
        anon_client.post(SIGNUP_URL, VALID_PAYLOAD)
        user = User.objects.get(email=VALID_PAYLOAD["email"])
        assert user.otp_codes.filter(purpose="signup", used=False).exists()

    def test_signup_duplicate_email(self, anon_client, employee):
        """Signup with an already registered email returns 400."""
        payload = {**VALID_PAYLOAD, "email": employee.email}
        res = anon_client.post(SIGNUP_URL, payload)
        assert res.status_code == 400

    def test_signup_password_mismatch(self, anon_client):
        """Signup where password and password2 don't match returns 400."""
        payload = {**VALID_PAYLOAD, "password2": "wrongpass"}
        res = anon_client.post(SIGNUP_URL, payload)
        assert res.status_code == 400

    def test_signup_missing_email(self, anon_client):
        """Signup without an email field returns 400."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "email"}
        res = anon_client.post(SIGNUP_URL, payload)
        assert res.status_code == 400

    def test_signup_missing_username(self, anon_client):
        """Signup without a username field returns 400."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "username"}
        res = anon_client.post(SIGNUP_URL, payload)
        assert res.status_code == 400
