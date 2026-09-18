from django.urls import path
from .views import CartItemPersonalizationAPIView, PersonalizationPhotoDetailAPIView

urlpatterns = [
    path("cart-item/<int:cart_item_id>/", CartItemPersonalizationAPIView.as_view()),
    path(
        "cart-item/<int:cart_item_id>/photos/<int:photo_id>/",
        PersonalizationPhotoDetailAPIView.as_view(),
    ),
]
