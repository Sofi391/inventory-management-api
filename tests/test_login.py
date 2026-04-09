import pytest

LOGIN_URL = "/accounts/login/"


@pytest.mark.django_db
class TestLogin:

    def test_login_success(self, anon_client, employee):
        """Valid credentials return 200 with access and refresh JWT tokens."""
        res = anon_client.post(LOGIN_URL, {"email": employee.email, "password": "pass1234"})
        assert res.status_code == 200
        assert "access" in res.data
        assert "refresh" in res.data

    def test_login_wrong_password(self, anon_client, employee):
        """Correct email but wrong password returns 400."""
        res = anon_client.post(LOGIN_URL, {"email": employee.email, "password": "wrongpass"})
        assert res.status_code == 400

    def test_login_unknown_email(self, anon_client):
        """Login attempt with an email that doesn't exist returns 400."""
        res = anon_client.post(LOGIN_URL, {"email": "ghost@test.com", "password": "pass1234"})
        assert res.status_code == 400

    def test_login_inactive_user(self, anon_client, db):
        """Login attempt for an unverified inactive account returns 400."""
        from django.contrib.auth.models import User
        inactive = User.objects.create_user(
            username="inactive", email="inactive@test.com", password="pass1234", is_active=False
        )
        res = anon_client.post(LOGIN_URL, {"email": inactive.email, "password": "pass1234"})
        assert res.status_code == 400

    def test_login_missing_email(self, anon_client):
        """Login request without an email field returns 400."""
        res = anon_client.post(LOGIN_URL, {"password": "pass1234"})
        assert res.status_code == 400

    def test_login_missing_password(self, anon_client, employee):
        """Login request without a password field returns 400."""
        res = anon_client.post(LOGIN_URL, {"email": employee.email})
        assert res.status_code == 400
