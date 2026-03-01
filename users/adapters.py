from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.shortcuts import redirect

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        next_url = request.GET.get("next")
        return next_url or settings.LOGIN_REDIRECT_URL
