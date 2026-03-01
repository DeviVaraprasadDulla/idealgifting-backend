# orders/models.py

import uuid
from django.db import models
from django.contrib.auth.models import User


# ============================================
# ADDRESS MODEL
# ============================================

class Address(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        null=True,
        blank=True
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)

    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)

    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10)
    country = models.CharField(max_length=50, default="India")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} - {self.city}"


# ============================================
# ORDER MODEL
# ============================================

class Order(models.Model):

    PAYMENT_STATUS = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    )

    ORDER_STATUS = (
        ("PLACED", "Order Placed"),
        ("CONFIRMED", "Confirmed"),
        ("PACKED", "Packed"),
        ("SHIPPED", "Shipped"),
        ("OUT_FOR_DELIVERY", "Out for Delivery"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True
    )

    public_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="PENDING"
    )

    order_status = models.CharField(
        max_length=30,
        choices=ORDER_STATUS,
        default="PLACED"
    )

    tracking_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    courier_name = models.CharField(
        max_length=100,
        default="DTDC"
    )

    shipped_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # 🔥 PRODUCTION ORDER NUMBER
    @property
    def order_number(self):
        return f"IG-{str(self.id).zfill(6)}"

    def __str__(self):
        return f"{self.order_number} - {self.user.username if self.user else 'Guest'}"


# ============================================
# ORDER ITEMS
# ============================================

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    product_name = models.CharField(max_length=255)
    product_image = models.URLField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return self.product_name


# ============================================
# ORDER STATUS HISTORY
# ============================================

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history"
    )

    status = models.CharField(max_length=30)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"