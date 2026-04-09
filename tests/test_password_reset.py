import pytest
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from accounts.models import OtpCode

OTP_REQUEST_URL = "/accounts/otp/request/"
PASSWORD_RESET_URL = "/accounts/password-reset/"


@pytest.fixture
def reset_otp(employee):
    return OtpCode.objects.create(
        user=employee, code=654321, purpose="reset", used=False
    )


@pytest.mark.django_db
class TestOtpRequest:

    @patch("accounts.views.send_otp")
    def test_otp_request_success(self, mock_send, anon_client, employee):
        """Valid email triggers a reset OTP creation and returns 200."""
        res = anon_client.post(OTP_REQUEST_URL, {"email": employee.email})
        assert res.status_code == 200
        assert OtpCode.objects.filter(user=employee, purpose="reset", used=False).exists()

    def test_otp_request_unknown_email(self, anon_client):
        """OTP request for a non-existent email returns 400."""
        res = anon_client.post(OTP_REQUEST_URL, {"email": "nobody@test.com"})
        assert res.status_code == 400

    def test_otp_request_missing_email(self, anon_client):
        """OTP request with no email field returns 400."""
        res = anon_client.post(OTP_REQUEST_URL, {})
        assert res.status_code == 400


@pytest.mark.django_db
class TestPasswordReset:

    @patch("accounts.views.send_mail")
    def test_password_reset_success(self, mock_mail, anon_client, employee, reset_otp):
        """Valid OTP and matching new passwords resets the password and returns 200."""
        res = anon_client.post(PASSWORD_RESET_URL, {
            "otp": reset_otp.code,
            "password": "newpass1234",
            "password2": "newpass1234",
        })
        assert res.status_code == 200
        employee.refresh_from_db()
        assert employee.check_password("newpass1234")

    @patch("accounts.views.send_mail")
    def test_password_reset_marks_otp_used(self, mock_mail, anon_client, employee, reset_otp):
        """After a successful reset the OTP used flag is set to True."""
        anon_client.post(PASSWORD_RESET_URL, {
            "otp": reset_otp.code,
            "password": "newpass1234",
            "password2": "newpass1234",
        })
        reset_otp.refresh_from_db()
        assert reset_otp.used is True

    def test_password_reset_invalid_otp(self, anon_client):
        """Password reset with a non-existent OTP returns 400."""
        res = anon_client.post(PASSWORD_RESET_URL, {
            "otp": 000000,
            "password": "newpass1234",
            "password2": "newpass1234",
        })
        assert res.status_code == 400

    def test_password_reset_expired_otp(self, anon_client, reset_otp):
        """Password reset with an expired OTP (older than 5 minutes) returns 400."""
        reset_otp.created_at = timezone.now() - timedelta(minutes=10)
        reset_otp.save()
        res = anon_client.post(PASSWORD_RESET_URL, {
            "otp": reset_otp.code,
            "password": "newpass1234",
            "password2": "newpass1234",
        })
        assert res.status_code == 400

    def test_password_reset_password_mismatch(self, anon_client, reset_otp):
        """Password reset where password and password2 don't match returns 400."""
        res = anon_client.post(PASSWORD_RESET_URL, {
            "otp": reset_otp.code,
            "password": "newpass1234",
            "password2": "different1234",
        })
        assert res.status_code == 400

    def test_password_reset_same_password(self, anon_client, employee, reset_otp):
        """Password reset using the same current password returns 400."""
        res = anon_client.post(PASSWORD_RESET_URL, {
            "otp": reset_otp.code,
            "password": "pass1234",
            "password2": "pass1234",
        })
        assert res.status_code == 400

    def test_password_reset_already_used_otp(self, anon_client, reset_otp):
        """Password reset with an already used OTP returns 400."""
        reset_otp.used = True
        reset_otp.save()
        res = anon_client.post(PASSWORD_RESET_URL, {
            "otp": reset_otp.code,
            "password": "newpass1234",
            "password2": "newpass1234",
        })
        assert res.status_code == 400
