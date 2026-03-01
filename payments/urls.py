from django.urls import path
from .views import InitiatePaymentAPIView
from .webhooks import phonepe_webhook

urlpatterns = [
    path("initiate/", InitiatePaymentAPIView.as_view()),
    path("webhook/", phonepe_webhook),
]