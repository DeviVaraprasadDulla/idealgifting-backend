from django.urls import path
from .views import BannerListAPIView

urlpatterns = [
    path("banners/", BannerListAPIView.as_view()),
]
