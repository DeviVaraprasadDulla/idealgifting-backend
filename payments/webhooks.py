# payments/webhooks.py

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from payments.models import Payment
from orders.models import Order
from orders.views import MarkOrderPaidAPIView
import json


@csrf_exempt
def phonepe_webhook(request):

    data = json.loads(request.body)

    payment_id = data.get("payment_id")
    status = data.get("status")

    try:
        payment = Payment.objects.get(payment_id=payment_id)
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)

    if status == "SUCCESS":
        payment.status = "SUCCESS"
        payment.save()

        # Mark order paid
        order = payment.order
        order.payment_status = "PAID"
        order.order_status = "CONFIRMED"
        order.save()

    elif status == "FAILED":
        payment.status = "FAILED"
        payment.save()

    return JsonResponse({"message": "Webhook processed"})