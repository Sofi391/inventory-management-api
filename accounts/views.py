import logging
import time
from rest_framework import status, permissions
from rest_framework.generics import CreateAPIView
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from .serializers import (SignupSerializer,OtpVerificationSerializer,
                          OtpResendSerializer,LoginSerializer,OtpCodeSerializer,
                          PassResetSerializer,
                          )

logger = logging.getLogger('accounts')

def send_otp(otp):
    send_mail(
        subject="Your Verification Code",
        message=f"""
    Hello {otp.user.username},

    Your verification code is: {otp.code}

    This code is valid for the next 5 minutes. 
    Please use it to complete your action. 
    If you did not request this, please ignore this email.

    Thank you,
    The Inventory Management Team
    """,
        from_email=f"Inventory Management System<{settings.EMAIL_HOST_USER}>",
        recipient_list=[otp.user.email],
        fail_silently=False
    )


class SignupView(CreateAPIView):
    model = User
    serializer_class = SignupSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        start = time.time()
        logger.info("Signup attempt | email=%s", request.data.get('email'))
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.save()
            try:
                send_otp(otp)
                logger.info("OTP sent | user=%s | elapsed=%.3fs", otp.user.username, time.time() - start)
            except Exception as e:
                logger.error("Failed to send OTP | user=%s | error=%s", otp.user.username, e)
            return Response({'message': 'Otp sent successfully'}, status=status.HTTP_201_CREATED)
        logger.warning("Signup validation failed | errors=%s | elapsed=%.3fs", serializer.errors, time.time() - start)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOtpView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        start = time.time()
        logger.info("OTP verification attempt")
        serializer = OtpVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            try:
                send_mail(
                    subject="Welcome to Inventory Management System",
                    message=f"""
        Hello {user.username},

        Your account has been successfully verified.

        Welcome to the Inventory Management System! You can now login and start managing your inventory.

        Thank you,
        The Inventory Management Team
        """,
                    from_email=f"Inventory Management System<{settings.EMAIL_HOST_USER}>",
                    recipient_list=[user.email],
                    fail_silently=False
                )
            except Exception as e:
                logger.error("Failed to send welcome email | user=%s | error=%s", user.username, e)
            refresh = RefreshToken.for_user(user)
            logger.info("OTP verified | user=%s | elapsed=%.3fs", user.username, time.time() - start)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                "message": "Your account has been successfully verified and you are now logged in.",
            }, status=status.HTTP_200_OK)
        logger.warning("OTP verification failed | errors=%s | elapsed=%.3fs", serializer.errors, time.time() - start)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class OtpResendView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        start = time.time()
        logger.info("OTP resend attempt | email=%s", request.data.get('email'))
        serializer = OtpResendSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.save()
            try:
                send_otp(otp)
                logger.info("OTP resent | user=%s | elapsed=%.3fs", otp.user.username, time.time() - start)
            except Exception as e:
                logger.error("Failed to resend OTP | user=%s | error=%s", otp.user.username, e)
            return Response({'message': 'Otp sent successfully'}, status=status.HTTP_201_CREATED)
        logger.warning("OTP resend validation failed | errors=%s | elapsed=%.3fs", serializer.errors, time.time() - start)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        start = time.time()
        logger.info("Login attempt | email=%s", request.data.get('email'))
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            logger.info("Login successful | user=%s | elapsed=%.3fs", user.username, time.time() - start)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                "message": "Login successful."
            })
        logger.warning("Login failed | email=%s | errors=%s | elapsed=%.3fs", request.data.get('email'), serializer.errors, time.time() - start)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        start = time.time()
        logger.info("Logout attempt | user=%s", request.user)
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            logger.warning("Logout failed | reason=no refresh token | user=%s", request.user)
            return Response({'detail': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("Logout successful | user=%s | elapsed=%.3fs", request.user, time.time() - start)
            return Response({'detail': 'Successfully logged out'}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error("Logout error | user=%s | error=%s | elapsed=%.3fs", request.user, e, time.time() - start)
            return Response({'detail': 'Invalid or Expired Token'}, status=status.HTTP_400_BAD_REQUEST)


class OtpRequestView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        start = time.time()
        logger.info("Password reset OTP request | email=%s", request.data.get('email'))
        serializer = OtpCodeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            otp = serializer.instance
            try:
                send_otp(otp)
                logger.info("Password reset OTP sent | user=%s | elapsed=%.3fs", otp.user.username, time.time() - start)
            except Exception as e:
                logger.error("Failed to send password reset OTP | user=%s | error=%s", otp.user.username, e)
            return Response({"message": "OTP code sent successfully"}, status=status.HTTP_200_OK)
        logger.warning("Password reset OTP request failed | errors=%s | elapsed=%.3fs", serializer.errors, time.time() - start)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        start = time.time()
        logger.info("Password reset attempt")
        serializer = PassResetSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            try:
                send_mail(
                    subject="Your Password Has Been Reset",
                    message=f"""
            Hello {user.username},

            This is a confirmation that your account password has been successfully reset.
            If you did not request this change, please contact our support team immediately.

            Thank you,
            The Inventory Management Team
            """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
            except Exception as e:
                logger.error("Failed to send password reset confirmation | user=%s | error=%s", user.username, e)
            logger.info("Password reset successful | user=%s | elapsed=%.3fs", user.username, time.time() - start)
            return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)
        logger.warning("Password reset failed | errors=%s | elapsed=%.3fs", serializer.errors, time.time() - start)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

