# settings_app/urls.py

from django.urls import path
from .views import ActiveAnnouncementAPIView

urlpatterns = [
    path("announcement/", ActiveAnnouncementAPIView.as_view()),
]
