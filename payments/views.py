# payments/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
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

        try:

            order = Order.objects.select_related(
                "user"
            ).get(
                public_token=order_token,
                user=request.user
            )

        except Order.DoesNotExist:

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
                return Response(
                    {"error": "Payment record not found"},
                    status=400
                )
            if payment and (
                payment.razorpay_order_id
                != request.data.get("razorpay_order_id")
            ):
                return Response(
                    {"error": "Invalid payment reference"},
                    status=400
                )
            
            payment.razorpay_payment_id = request.data.get(
                    "razorpay_payment_id"
                )
            payment.status = "SUCCESS"
            payment.save()

        except Exception:

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

        try:
            send_order_email(
                order.user.email,
                order
            )
        except Exception as e:
            print("Email Error:", e)

        return Response(
            {
                "message":
                "Payment successful"
            }
        )