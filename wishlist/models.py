from django.db import models
from django.contrib.auth.models import User
from products.models import Product


class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wishlist")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s wishlist"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("wishlist", "product")
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.wishlist.user.username} - {self.product.name}"
