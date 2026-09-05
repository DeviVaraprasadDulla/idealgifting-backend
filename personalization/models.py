from django.db import models


def personalization_upload_path(instance, filename):
    return f"personalizations/{instance.cart_item_id or 'new'}/{filename}"


class Personalization(models.Model):
    """
    Holds a customer's personalisation choices (name/date/message/style +
    an uploaded photo) for a single cart line. Attached via a nullable
    OneToOne on the *personalization* side, so the existing CartItem model
    and its (cart, product) uniqueness are never touched.
    """

    cart_item = models.OneToOneField(
        "cart.CartItem",
        on_delete=models.CASCADE,
        related_name="personalization",
    )

    names = models.CharField(max_length=255, blank=True)
    date = models.CharField(max_length=100, blank=True)
    message = models.CharField(max_length=300, blank=True)
    style = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(
        upload_to=personalization_upload_path, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Personalization for cart item #{self.cart_item_id}"

    def to_snapshot(self, request=None):
        """Plain-dict representation safe to store on OrderItem at order
        creation time, so personalisation survives even if this row or its
        parent CartItem is later deleted (e.g. cart clearing on payment)."""
        photo_url = None
        if self.photo:
            photo_url = (
                request.build_absolute_uri(self.photo.url)
                if request
                else self.photo.url
            )

        return {
            "names": self.names,
            "date": self.date,
            "message": self.message,
            "style": self.style,
            "photo_url": photo_url,
        }
