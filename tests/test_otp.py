import pytest
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from accounts.models import OtpCode

VERIFY_URL = "/accounts/verify/otp/"
RESEND_URL = "/accounts/otp/resend/"


@pytest.fixture
def inactive_user(db):
    return User.objects.create_user(
        username="inactive", email="inactive@test.com", password="pass1234", is_active=False
    )


@pytest.fixture
def signup_otp(inactive_user):
    return OtpCode.objects.create(
        user=inactive_user, code=123456, purpose="signup", used=False
    )


@pytest.mark.django_db
class TestOtpVerification:

    @patch("accounts.views.send_mail")
    def test_verify_otp_success(self, mock_mail, anon_client, signup_otp, inactive_user):
        """Valid OTP returns 200 with JWT tokens and activates the user account."""
        res = anon_client.post(VERIFY_URL, {"otp": signup_otp.code})
        assert res.status_code == 200
        assert "access" in res.data
        assert "refresh" in res.data
        inactive_user.refresh_from_db()
        assert inactive_user.is_active is True

    @patch("accounts.views.send_mail")
    def test_verify_otp_marks_used(self, mock_mail, anon_client, signup_otp):
        """After successful verification the OTP used flag is set to True."""
        anon_client.post(VERIFY_URL, {"otp": signup_otp.code})
        signup_otp.refresh_from_db()
        assert signup_otp.used is True

    def test_verify_invalid_otp(self, anon_client):
        """A non-existent OTP code returns 400."""
        res = anon_client.post(VERIFY_URL, {"otp": 000000})
        assert res.status_code == 400

    def test_verify_already_used_otp(self, anon_client, signup_otp):
        """An OTP that was already used returns 400."""
        signup_otp.used = True
        signup_otp.save()
        res = anon_client.post(VERIFY_URL, {"otp": signup_otp.code})
        assert res.status_code == 400

    def test_verify_expired_otp(self, anon_client, signup_otp):
        """An OTP older than 5 minutes returns 400 with expiry error."""
        signup_otp.created_at = timezone.now() - timedelta(minutes=10)
        signup_otp.save()
        res = anon_client.post(VERIFY_URL, {"otp": signup_otp.code})
        assert res.status_code == 400


@pytest.mark.django_db
class TestOtpResend:

    @patch("accounts.views.send_otp")
    def test_resend_otp_success(self, mock_send, anon_client, inactive_user):
        """Resend OTP for an inactive user returns 201 and creates a fresh OTP."""
        res = anon_client.post(RESEND_URL, {"email": inactive_user.email})
        assert res.status_code == 201
        assert OtpCode.objects.filter(user=inactive_user, purpose="signup", used=False).exists()

    def test_resend_otp_active_user(self, anon_client, employee):
        """Resend OTP for an already active user returns 400."""
        res = anon_client.post(RESEND_URL, {"email": employee.email})
        assert res.status_code == 400

    def test_resend_otp_unknown_email(self, anon_client):
        """Resend OTP for a non-existent email returns 400."""
        res = anon_client.post(RESEND_URL, {"email": "ghost@test.com"})
        assert res.status_code == 400
