# cart/models.py

from django.db import models
from django.contrib.auth.models import User
from products.models import Product, ProductVariant


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

    # Selected size/page-count option, if this product has any. Null for
    # every product without variants (unchanged behaviour). A product
    # with two different variants in the same cart must occupy two
    # separate CartItem rows - see unique_together below.
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product", "variant")

    def __str__(self):
        variant_label = f" ({self.variant.label})" if self.variant else ""
        return f"{self.product.name}{variant_label} x {self.quantity}"