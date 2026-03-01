from django.conf import settings
from .dummy import DummyPaymentService
from .phonepe import PhonePePaymentService


def get_payment_service():
    if settings.PAYMENT_MODE == "PHONEPE":
        return PhonePePaymentService()
    return DummyPaymentService()