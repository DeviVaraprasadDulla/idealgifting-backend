# payments/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from .services.factory import get_payment_service


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