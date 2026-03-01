from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import SignupView, LoginView, LogoutView,MeAPIView,GoogleLoginAPIView,SendResetOTPAPIView,VerifyResetOTPAPIView
urlpatterns = [
    path("signup/", SignupView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeAPIView.as_view()),
    # users/urls.py
    path("google-login/", GoogleLoginAPIView.as_view()),
    path("auth/reset/send-otp/", SendResetOTPAPIView.as_view()),
    path("auth/reset/verify-otp/", VerifyResetOTPAPIView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),


]
