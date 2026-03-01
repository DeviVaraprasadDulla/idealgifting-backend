# payments/models.py

from django.db import models
from django.contrib.auth.models import User
from orders.models import Order


class Payment(models.Model):

    STATUS_CHOICES = (
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("PENDING", "Pending"),
    )

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    payment_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    payment_method = models.CharField(
        max_length=50,
        default="PHONEPE"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.order.id} - {self.status}"