# payments/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from payments.emails import send_admin_order_mail
from .services.factory import get_payment_service
from .services.razorpay import RazorpayService
from backend import settings
from django.db.models import F
from .models import Payment
from cart.models import CartItem

from orders.models import (
    Order,
    OrderStatusHistory
)
import logging

logger = logging.getLogger(__name__)
from orders.utils import send_order_email
class InitiatePaymentAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        order_id = request.data.get("order_id")

        if not order_id:
            return Response({"error": "order_id required"}, status=400)

        try:
            order = Order.objects.get(
                id=order_id,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if order.payment_status == "PAID":
            return Response(
                {"error": "Order already paid"},
                status=400
            )

        service = get_payment_service()
        result = service.initiate_payment(order)

        return Response(result)
    

class CreateRazorpayOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        order_token = request.data.get(
            "order_token"
        )

        try:

            order = Order.objects.get(
                public_token=order_token,
                user=request.user
            )

        except Order.DoesNotExist:

            return Response(
                {"error": "Order not found"},
                status=404
            )

        razorpay_order = (
            RazorpayService.create_order(order)
        )
        Payment.objects.filter(
            order=order,
            status="PENDING"
        ).delete()
        Payment.objects.create(
            user=order.user,
            order=order,
            razorpay_order_id=razorpay_order["id"],
            payment_method="RAZORPAY",
            amount=order.total_amount,
            status="PENDING"
        )
        return Response(
            {
                "key":
                    settings.RAZORPAY_KEY_ID,

                "razorpay_order_id":
                razorpay_order["id"],

                "amount":
                razorpay_order["amount"]
            }
        )
    

class VerifyRazorpayPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        order_token = request.data.get(
            "order_token"
        )
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")

        print(
            f"[PAYMENT_VERIFY] Incoming verification: token={order_token}, rzp_order={razorpay_order_id}, rzp_payment={razorpay_payment_id}, user={request.user}",
            flush=True
        )
        logger.info(
            f"[PAYMENT_VERIFY] Incoming verification: token={order_token}, rzp_order={razorpay_order_id}, rzp_payment={razorpay_payment_id}, user={request.user}"
        )

        try:

            order = Order.objects.select_related(
                "user"
            ).get(
                public_token=order_token,
                user=request.user
            )

        except Order.DoesNotExist:
            print(f"[PAYMENT_VERIFY_ERROR] Order not found for token={order_token} and user={request.user}", flush=True)
            logger.error(f"[PAYMENT_VERIFY_ERROR] Order not found for token={order_token} and user={request.user}")
            return Response(
                {"error": "Order not found"},
                status=404
            )

        try:

            RazorpayService.verify_signature(
                {
                    "razorpay_order_id":
                    request.data.get(
                        "razorpay_order_id"
                    ),

                    "razorpay_payment_id":
                    request.data.get(
                        "razorpay_payment_id"
                    ),

                    "razorpay_signature":
                    request.data.get(
                        "razorpay_signature"
                    )
                }
            )
            # ADD THIS BLOCK HERE
            payment = Payment.objects.filter(
                order=order,
                status="PENDING"
            ).last()
            if not payment:
                print(f"[PAYMENT_VERIFY_ERROR] No PENDING Payment record found for Order #{order.order_number}", flush=True)
                logger.error(f"[PAYMENT_VERIFY_ERROR] No PENDING Payment record found for Order #{order.order_number}")
                return Response(
                    {"error": "Payment record not found"},
                    status=400
                )
            if payment and (
                payment.razorpay_order_id
                != request.data.get("razorpay_order_id")
            ):
                print(f"[PAYMENT_VERIFY_ERROR] Mismatched razorpay_order_id: expected {payment.razorpay_order_id}, got {request.data.get('razorpay_order_id')}", flush=True)
                logger.error(f"[PAYMENT_VERIFY_ERROR] Mismatched razorpay_order_id: expected {payment.razorpay_order_id}, got {request.data.get('razorpay_order_id')}")
                return Response(
                    {"error": "Invalid payment reference"},
                    status=400
                )
            
            payment.razorpay_payment_id = request.data.get(
                    "razorpay_payment_id"
                )
            payment.status = "SUCCESS"
            payment.save()
            print(f"[PAYMENT_VERIFY_SUCCESS] Payment signature verified and record updated to SUCCESS for Order #{order.order_number}", flush=True)
            logger.info(f"[PAYMENT_VERIFY_SUCCESS] Payment signature verified and record updated to SUCCESS for Order #{order.order_number}")

        except Exception as e:
            print(f"[PAYMENT_VERIFY_ERROR] Signature verification exception for Order #{order.order_number}: {e}", flush=True)
            logger.exception(f"[PAYMENT_VERIFY_ERROR] Signature verification exception for Order #{order.order_number}: {e}")

            payment = Payment.objects.filter(
                order=order,
                status="PENDING"
            ).last()

            if payment:
                payment.razorpay_payment_id = request.data.get(
                    "razorpay_payment_id"
                )
                payment.status = "FAILED"
                payment.save()

            return Response(
                {
                    "error":
                    "Payment verification failed"
                },
                status=400
            )

        if order.payment_status == "PAID":
            print(f"[PAYMENT_VERIFY_NOTICE] Order #{order.order_number} was already marked as PAID", flush=True)
            logger.info(f"[PAYMENT_VERIFY_NOTICE] Order #{order.order_number} was already marked as PAID")
            return Response(
                {"message": "Already paid"}
            )

        order.payment_status = "PAID"

        order.order_status = "CONFIRMED"

        order.save()

        OrderStatusHistory.objects.create(
            order=order,
            status="CONFIRMED"
        )

        for item in order.items.select_related(
            "product"
        ):
            item.product.__class__.objects.filter(
                pk=item.product.pk
            ).update(
                stock=F("stock") - item.quantity
            )

        CartItem.objects.filter(
            cart__user=order.user
        ).delete()

        customer_email = order.user.email if order.user else None
        admin_email = getattr(settings, "ADMIN_EMAIL", None)

        # 1. Customer Email
        try:
            print(f"📨 PAYMENT: Starting customer email for Order #{order.order_number}", flush=True)
            logger.info(f"PAYMENT: Starting customer email for Order #{order.order_number}")
            if customer_email:
                print(f"📧 [CUSTOMER EMAIL] Connecting to SMTP and sending to {customer_email}...", flush=True)
                logger.info(f"[CUSTOMER EMAIL] Connecting to SMTP and sending to {customer_email}...")
                send_order_email(
                    customer_email,
                    order
                )
                print(f"✅ [CUSTOMER EMAIL] Sent successfully to {customer_email}", flush=True)
                logger.info(f"[CUSTOMER EMAIL] Sent successfully to {customer_email}")
            else:
                print(f"⚠️ [CUSTOMER EMAIL] Skipped: No email address for user {order.user}", flush=True)
                logger.warning(f"[CUSTOMER EMAIL] Skipped: No email address for user {order.user}")
        except Exception as e:
            print(f"❌ [CUSTOMER EMAIL] Failed for Order #{order.order_number}: {e}", flush=True)
            logger.exception(f"[CUSTOMER EMAIL] Failed for Order #{order.order_number}: {e}")

        # 2. Admin Email
        try:
            print(f"📨 PAYMENT: Starting admin email for Order #{order.order_number}", flush=True)
            logger.info(f"PAYMENT: Starting admin email for Order #{order.order_number}")
            print(f"📧 [ADMIN EMAIL] Connecting to SMTP and sending to {admin_email}...", flush=True)
            logger.info(f"[ADMIN EMAIL] Connecting to SMTP and sending to {admin_email}...")
            send_admin_order_mail(order)
            print(f"✅ [ADMIN EMAIL] Sent successfully to {admin_email}", flush=True)
            logger.info(f"[ADMIN EMAIL] Sent successfully to {admin_email}")
        except Exception as e:
            print(f"❌ [ADMIN EMAIL] Failed for Order #{order.order_number}: {e}", flush=True)
            logger.exception(f"[ADMIN EMAIL] Failed for Order #{order.order_number}: {e}")

        return Response(
            {
                "message":
                "Payment successful"
            }
        )