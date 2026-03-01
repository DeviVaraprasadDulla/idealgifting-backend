# payments/services/dummy.py

from payments.models import Payment
from orders.models import Order
from django.utils import timezone


class DummyPaymentService:

    def initiate_payment(self, order: Order):

        # Create payment record
        Payment.objects.create(
            user=order.user,
            order=order,
            payment_id=f"DUMMY-{order.id}",
            payment_method="DUMMY",
            amount=order.total_amount,
            status="SUCCESS",
        )

        # Immediately mark order as paid (development mode)
        order.payment_status = "PAID"
        order.order_status = "CONFIRMED"
        order.save()

        return {
            "payment_status": "PAID",
            "message": "Dummy payment successful"
        }