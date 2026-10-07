from payments.models import Payment
from orders.models import Order
from django.utils import timezone
from orders.utils import send_order_email
from payments.emails import send_admin_order_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


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

        print(f"[DUMMY_PAYMENT] Order #{order.order_number} marked as PAID. Sending emails...", flush=True)
        logger.info(f"[DUMMY_PAYMENT] Order #{order.order_number} marked as PAID. Sending emails...")

        customer_email = order.user.email if order.user else None

        try:
            if customer_email:
                send_order_email(customer_email, order)
                print(f"[SUCCESS] [Order #{order.order_number}] Dummy payment customer email sent", flush=True)
                logger.info(f"[SUCCESS] [Order #{order.order_number}] Dummy payment customer email sent to {customer_email}")
        except Exception as e:
            print(f"[FAILED] [Order #{order.order_number}] Dummy payment customer email failed: {e}", flush=True)
            logger.exception(f"[FAILED] [Order #{order.order_number}] Dummy payment customer email failed: {e}")

        try:
            send_admin_order_mail(order)
            print(f"[SUCCESS] [Order #{order.order_number}] Dummy payment admin email sent", flush=True)
            logger.info(f"[SUCCESS] [Order #{order.order_number}] Dummy payment admin email sent to {settings.ADMIN_EMAIL}")
        except Exception as e:
            print(f"[FAILED] [Order #{order.order_number}] Dummy payment admin email failed: {e}", flush=True)
            logger.exception(f"[FAILED] [Order #{order.order_number}] Dummy payment admin email failed: {e}")

        return {
            "payment_status": "PAID",
            "message": "Dummy payment successful"
        }