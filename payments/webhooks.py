# payments/webhooks.py

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from payments.models import Payment
from orders.models import Order
from orders.views import MarkOrderPaidAPIView
import json


from orders.utils import send_order_email
from payments.emails import send_admin_order_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def phonepe_webhook(request):

    data = json.loads(request.body)

    payment_id = data.get("payment_id")
    status = data.get("status")

    print(f"[PHONEPE_WEBHOOK] Received webhook for payment_id={payment_id}, status={status}", flush=True)
    logger.info(f"[PHONEPE_WEBHOOK] Received webhook for payment_id={payment_id}, status={status}")

    try:
        payment = Payment.objects.get(payment_id=payment_id)
    except Payment.DoesNotExist:
        print(f"[PHONEPE_WEBHOOK_ERROR] Payment not found for payment_id={payment_id}", flush=True)
        logger.error(f"[PHONEPE_WEBHOOK_ERROR] Payment not found for payment_id={payment_id}")
        return JsonResponse({"error": "Payment not found"}, status=404)

    if status == "SUCCESS":
        payment.status = "SUCCESS"
        payment.save()

        # Mark order paid
        order = payment.order
        order.payment_status = "PAID"
        order.order_status = "CONFIRMED"
        order.save()

        print(f"[PHONEPE_WEBHOOK] Order #{order.order_number} marked as PAID. Dispatching emails...", flush=True)
        customer_email = order.user.email if order.user else None

        try:
            if customer_email:
                send_order_email(customer_email, order)
                print(f"[SUCCESS] [Order #{order.order_number}] PhonePe customer email sent", flush=True)
                logger.info(f"[SUCCESS] [Order #{order.order_number}] PhonePe customer email sent to {customer_email}")
        except Exception as e:
            print(f"[FAILED] [Order #{order.order_number}] PhonePe customer email failed: {e}", flush=True)
            logger.exception(f"[FAILED] [Order #{order.order_number}] PhonePe customer email failed: {e}")

        try:
            send_admin_order_mail(order)
            print(f"[SUCCESS] [Order #{order.order_number}] PhonePe admin email sent", flush=True)
            logger.info(f"[SUCCESS] [Order #{order.order_number}] PhonePe admin email sent to {settings.ADMIN_EMAIL}")
        except Exception as e:
            print(f"[FAILED] [Order #{order.order_number}] PhonePe admin email failed: {e}", flush=True)
            logger.exception(f"[FAILED] [Order #{order.order_number}] PhonePe admin email failed: {e}")

    elif status == "FAILED":
        payment.status = "FAILED"
        payment.save()
        print(f"[PHONEPE_WEBHOOK] Payment marked as FAILED for payment_id={payment_id}", flush=True)

    return JsonResponse({"message": "Webhook processed"})