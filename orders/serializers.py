from rest_framework import serializers
from .models import Order, OrderItem, Address


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class OrderItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="product_name")
    image = serializers.CharField(source="product_image")
    personalization = serializers.JSONField(source="personalization_snapshot")

    class Meta:
        model = OrderItem
        fields = ["name", "image", "price", "quantity", "personalization"]


class OrderSerializer(serializers.ModelSerializer):
    order_number = serializers.ReadOnlyField()
    address = AddressSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",  # 🔥 THIS WAS MISSING
            "payment_status",
            "order_status",
            "total_amount",
            "tracking_id",
            "created_at",
            "address",
            "items",
        ]