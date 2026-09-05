from django.urls import path
from .views import WishlistAPIView, WishlistRemoveAPIView, WishlistToggleAPIView

urlpatterns = [
    path("", WishlistAPIView.as_view()),
    path("toggle/", WishlistToggleAPIView.as_view()),
    path("<int:product_id>/", WishlistRemoveAPIView.as_view()),
]
