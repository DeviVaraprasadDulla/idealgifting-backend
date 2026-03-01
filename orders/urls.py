from django.urls import path
from .views import (
    CreateOrderAPIView,
    OrderByTokenAPIView,
    MyOrdersAPIView,
    SaveAddressAPIView,
    AddressListAPIView,
    UpdateAddressAPIView,
    DeleteAddressAPIView,
    OrderTrackingAPIView,
    MarkOrderPaidAPIView,
    CancelOrderAPIView
)

urlpatterns = [

    # ============================================
    # ORDER ROUTES
    # ============================================

    # Create order (Checkout step)
    path(
        "create/",
        CreateOrderAPIView.as_view(),
        name="order-create"
    ),

    # List all PAID orders of logged-in user
    path(
        "",
        MyOrdersAPIView.as_view(),
        name="my-orders"
    ),

    # Get single order by public token (Success Page)
    path(
        "by-token/<uuid:token>/",
        OrderByTokenAPIView.as_view(),
        name="order-by-token"
    ),

    # Track order (DTDC tracking timeline)
 path(
    "track/<uuid:token>/",
    OrderTrackingAPIView.as_view(),
    name="order-tracking"
),

    # Internal/Webhook route to mark order as PAID
    path(
        "mark-paid/",
        MarkOrderPaidAPIView.as_view(),
        name="mark-order-paid"
    ),

    # ============================================
    # ADDRESS ROUTES
    # ============================================

    # Save new address
    path(
        "save-address/",
        SaveAddressAPIView.as_view(),
        name="save-address"
    ),

    # List all user addresses
    path(
        "addresses/",
        AddressListAPIView.as_view(),
        name="address-list"
    ),

    # Update address
    path(
        "addresses/<int:pk>/update/",
        UpdateAddressAPIView.as_view(),
        name="update-address"
    ),

    # Delete address
    path(
        "addresses/<int:pk>/delete/",
        DeleteAddressAPIView.as_view(),
        name="delete-address"
    ),
    path("cancel/<uuid:token>/", CancelOrderAPIView.as_view()),
]