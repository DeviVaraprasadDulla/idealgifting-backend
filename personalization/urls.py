from django.urls import path
from .views import CartItemPersonalizationAPIView

urlpatterns = [
    path("cart-item/<int:cart_item_id>/", CartItemPersonalizationAPIView.as_view()),
]
