from django.urls import path
from .views import InitiatePaymentAPIView
from .webhooks import phonepe_webhook
from .views import (
    CreateRazorpayOrderAPIView,
    VerifyRazorpayPaymentAPIView
)
urlpatterns = [
    path("initiate/", InitiatePaymentAPIView.as_view()),
    path("webhook/", phonepe_webhook),
        path(
        "create-order/",
        CreateRazorpayOrderAPIView.as_view()
    ),

    path(
        "verify/",
        VerifyRazorpayPaymentAPIView.as_view()
    )

]