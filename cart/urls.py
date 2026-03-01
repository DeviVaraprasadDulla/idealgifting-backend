from django.urls import path
from .views import AddToCartAPIView, CartItemListAPIView,UpdateCartItemAPIView,RemoveCartItemAPIView,CheckoutAPIView

urlpatterns = [
    path("add/", AddToCartAPIView.as_view()),
    path("items/", CartItemListAPIView.as_view()),
    path("update/<int:pk>/", UpdateCartItemAPIView.as_view(), name="cart-update"),
        path("remove/<int:pk>/", RemoveCartItemAPIView.as_view(), name="cart-remove"),
    path("checkout/", CheckoutAPIView.as_view(), name="cart-checkout"),


]
