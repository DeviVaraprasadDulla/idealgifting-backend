from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import SignupSerializer

from cart.utils import merge_guest_cart_to_user

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created"}, status=201)

        return Response(serializer.errors, status=400)




class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"error": "Invalid credentials"}, status=401)

        # 🔥 MERGE GUEST CART → USER CART
        guest_id = request.headers.get("X-GUEST-ID")
        if guest_id:
            merge_guest_cart_to_user(guest_id, user)

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        })




class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        return Response({"message": "Logged out successfully"})




class MeAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "email": user.email,
            "username": user.username,
        })


class GoogleLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({"error": "Google token required"}, status=400)

        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            email = idinfo["email"]
            name = idinfo.get("name", "")

            user, _ = User.objects.get_or_create(
                username=email,
                defaults={
                    "email": email,
                    "first_name": name,
                }
            )
            guest_id = request.headers.get("X-GUEST-ID")
            if guest_id:
                merge_guest_cart_to_user(guest_id, user)

            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                }
            })

        except Exception:
            return Response({"error": "Invalid Google token"}, status=401)


import random
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.conf import settings
from .models import PasswordResetOTP


class SendResetOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email required"}, status=400)

        try:
            user = User.objects.filter(email=email).first()
        except User.DoesNotExist:
            return Response({"message": "If email exists, OTP sent"})

        otp = str(random.randint(100000, 999999))

        PasswordResetOTP.objects.filter(user=user).delete()

        PasswordResetOTP.objects.create(user=user, otp=otp)

        send_mail(
            subject="Your Password Reset OTP",
            message=f"Your OTP is {otp}. It is valid for 5 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        return Response({"message": "OTP sent"})


from .models import PasswordResetOTP


class VerifyResetOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        password = request.data.get("password")

        if not all([email, otp, password]):
            return Response({"error": "Invalid data"}, status=400)

        try:
            user = User.objects.filter(email=email).first()
            reset_otp = PasswordResetOTP.objects.get(user=user, otp=otp)
        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            return Response({"error": "Invalid OTP"}, status=400)

        if reset_otp.is_expired():
            reset_otp.delete()
            return Response({"error": "OTP expired"}, status=400)

        user.set_password(password)
        user.save()
        reset_otp.delete()

        return Response({"message": "Password reset successful"})
