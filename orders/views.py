"""
orders/views.py
Final Production-Level Order System
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.db import transaction
from django.db.models import F
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from cart.models import CartItem
from cart.utils import get_cart

from .models import (
    Order,
    Address,
    OrderStatusHistory,
    OrderItem
)
from .utils import send_order_email
from .utils import send_cancel_email



# ============================================================
# CREATE ORDER (CHECKOUT STEP)
# ============================================================

class CreateOrderAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        cart = get_cart(
            user=request.user,
            guest_id=request.headers.get("X-GUEST-ID")
        )

        if not cart:
            return Response({"error": "Cart expired"}, status=400)

        items = CartItem.objects.select_related("product").filter(cart=cart)

        if not items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        address_id = request.data.get("address_id")

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"error": "Invalid address"}, status=404)

        # 🔒 STOCK VALIDATION
        for item in items:
            if item.quantity > item.product.stock:
                return Response(
                    {
                        "error": f"{item.product.name} has only {item.product.stock} left"
                    },
                    status=400
                )

        total = sum(item.product.price * item.quantity for item in items)

        order = Order.objects.create(
            user=request.user,
            address=address,
            total_amount=total,
            payment_status="PENDING",
            order_status="PLACED"
        )

        OrderStatusHistory.objects.create(order=order, status="PLACED")

        request_scheme = request.scheme
        request_host = request.get_host()

        for item in items:

            first_image = item.product.images.first()
            image_url = ""

            if first_image:
                image_url = f"{request_scheme}://{request_host}{first_image.image.url}"

            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                product_image=image_url,
                price=item.product.price,
                quantity=item.quantity
            )

        return Response({
            "order_id": order.id,
            "order_token": str(order.public_token),
            "total_amount": order.total_amount,
            "payment_status": order.payment_status
        })


# ============================================================
# PAYMENT WEBHOOK (MARK ORDER AS PAID)
# ============================================================

class MarkOrderPaidAPIView(APIView):

    @transaction.atomic
    def post(self, request):

        order_token = request.data.get("order_token")

        try:
            order = Order.objects.select_related("user").get(public_token=order_token)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if order.payment_status == "PAID":
            return Response({"message": "Already paid"})

        # Update payment state
        order.payment_status = "PAID"
        order.order_status = "CONFIRMED"
        order.save()
        send_order_email(order.user.email, order)

        OrderStatusHistory.objects.create(order=order, status="CONFIRMED")

        # Reduce stock safely
        for item in order.items.select_related("product"):
            item.product.stock = F("stock") - item.quantity
            item.product.save()

        # Clear user cart
        CartItem.objects.filter(cart__user=order.user).delete()

        return Response({"message": "Order marked as PAID"})


# ============================================================
# GET ORDER BY TOKEN (SUCCESS PAGE)
# ============================================================

class OrderByTokenAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, token):

        try:
            order = Order.objects.select_related(
                "address"
            ).prefetch_related("items").get(
                public_token=token,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        address = order.address

        return Response({
            "id": order.id,
            "order_number": order.order_number,  # ✅ ADD THIS LINE
            "payment_status": order.payment_status,
            "order_status": order.order_status,
            "total_amount": order.total_amount,
            "tracking_id": order.tracking_id,
            "created_at": order.created_at,
            "address": {
                "first_name": address.first_name,
                "last_name": address.last_name,
                "phone": address.phone,
                "address_line1": address.address_line1,
                "address_line2": address.address_line2,
                "city": address.city,
                "state": address.state,
                "zip_code": address.zip_code,
            },
            "items": [
                {
                    "name": i.product_name,
                    "image": i.product_image,
                    "price": i.price,
                    "quantity": i.quantity
                }
                for i in order.items.all()
            ]
        })


# ============================================================
# MY PAID ORDERS
# ============================================================

class MyOrdersAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        orders = Order.objects.filter(
            user=request.user,
            payment_status="PAID"
        ).order_by("-created_at")

        return Response([
            {
                "id": o.id,
                "order_token": str(o.public_token),
                "total_amount": o.total_amount,
                "order_status": o.order_status,
                "tracking_id": o.tracking_id,
                "created_at": o.created_at,
                "items": [
                    {
                        "name": i.product_name,
                        "image": i.product_image,
                        "price": i.price,
                        "quantity": i.quantity
                    }
                    for i in o.items.all()
                ]
            }
            for o in orders
        ])


# ============================================================
# ORDER TRACKING TIMELINE
# ============================================================

class OrderTrackingAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, token):

        try:
            order = Order.objects.prefetch_related(
                "status_history"
            ).get(
                public_token=token,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        return Response({
            "order_token": str(order.public_token),
            "order_status": order.order_status,
            "tracking_id": order.tracking_id,
            "created_at": order.created_at,
            "timeline": [
                {
                    "status": h.status,
                    "time": h.updated_at
                }
                for h in order.status_history.all().order_by("updated_at")
            ]
        })


# ============================================================
# ADDRESS MANAGEMENT
# ============================================================

class SaveAddressAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        required_fields = [
            "first_name",
            "last_name",
            "phone",
            "address_line1",
            "city",
            "state",
            "zip_code",
        ]

        for field in required_fields:
            if not request.data.get(field):
                return Response(
                    {"error": f"{field} is required"},
                    status=400
                )

        address = Address.objects.create(
            user=request.user,
            first_name=request.data.get("first_name"),
            last_name=request.data.get("last_name"),
            phone=request.data.get("phone"),
            address_line1=request.data.get("address_line1"),
            address_line2=request.data.get("address_line2", ""),
            city=request.data.get("city"),
            state=request.data.get("state"),
            zip_code=request.data.get("zip_code"),
        )

        return Response({"message": "Address saved", "id": address.id}, status=201)


class AddressListAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        addresses = Address.objects.filter(user=request.user).order_by("-id")

        return Response([
            {
                "id": a.id,
                "first_name": a.first_name,
                "last_name": a.last_name,
                "phone": a.phone,
                "address_line1": a.address_line1,
                "city": a.city,
                "state": a.state,
                "zip_code": a.zip_code,
            }
            for a in addresses
        ])


class UpdateAddressAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):

        try:
            address = Address.objects.get(id=pk, user=request.user)
        except Address.DoesNotExist:
            return Response({"error": "Address not found"}, status=404)

        for field in [
            "first_name",
            "last_name",
            "phone",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "zip_code",
        ]:
            if field in request.data:
                setattr(address, field, request.data[field])

        address.save()

        return Response({"message": "Address updated"})


class DeleteAddressAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):

        try:
            address = Address.objects.get(id=pk, user=request.user)
            address.delete()
            return Response({"message": "Address deleted"})
        except ProtectedError:
            return Response(
                {"error": "Address used in orders. Cannot delete."},
                status=400
            )
        except Address.DoesNotExist:
            return Response({"error": "Address not found"}, status=404)
# ============================================================
# CANCEL ORDER
# ============================================================

class CancelOrderAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, token):

        try:
            order = Order.objects.prefetch_related("items").get(
                public_token=token,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        # 🚫 Already cancelled
        if order.order_status == "CANCELLED":
            return Response({"error": "Order already cancelled"}, status=400)

        # 🚫 Cannot cancel after shipping
        if order.order_status in [
            "SHIPPED",
            "OUT_FOR_DELIVERY",
            "DELIVERED"
        ]:
            return Response(
                {"error": "Order cannot be cancelled after shipping"},
                status=400
            )

        # ✅ Restore stock
        for item in order.items.select_related("product"):
            item.product.stock = F("stock") + item.quantity
            item.product.save()

        # ✅ Update order
        order.order_status = "CANCELLED"
        order.payment_status = "REFUNDED"
        order.save()
        send_cancel_email(order.user.email, order)

        OrderStatusHistory.objects.create(
            order=order,
            status="CANCELLED"
        )

        return Response({"message": "Order cancelled successfully"})