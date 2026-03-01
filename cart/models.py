# cart/models.py

from django.db import models
from django.contrib.auth.models import User
from products.models import Product


# ============================================
# CART MODEL
# ============================================

class Cart(models.Model):

    user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="cart"
    )

    # Guest cart identifier (UUID from frontend)
    guest_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"Cart(User: {self.user.username})"
        return f"Cart(Guest: {self.guest_id})"


# ============================================
# CART ITEM MODEL
# ============================================

class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"