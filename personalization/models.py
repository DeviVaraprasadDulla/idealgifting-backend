from django.db import models


def personalization_upload_path(instance, filename):
    return f"personalizations/{instance.cart_item_id or 'new'}/{filename}"


def personalization_photo_upload_path(instance, filename):
    return f"personalizations/{instance.personalization.cart_item_id}/{filename}"


class Personalization(models.Model):
    """
    Holds a customer's personalisation choices (name/date/message/style +
    uploaded photos) for a single cart line. Attached via a nullable
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

    # Deprecated: the original single-photo field. Kept (never dropped)
    # so any personalization row saved before multi-photo support was
    # added keeps its data intact. New saves no longer write to this -
    # they create PersonalizationPhoto rows instead (see below). Existing
    # rows that only have this field populated are migrated into a real
    # PersonalizationPhoto row by migration 0002, so to_snapshot() and
    # the API can always read from `photos` uniformly.
    photo = models.ImageField(
        upload_to=personalization_upload_path, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        count = self.photos.count()
        photo_bit = f", {count} photo{'s' if count != 1 else ''}" if count else ""
        return f"Personalization for cart item #{self.cart_item_id}{photo_bit}"

    def ordered_photos(self):
        photos = list(self.photos.all())
        if photos:
            return photos
        # Backward-compatibility fallback for any row that somehow still
        # only has the legacy single `photo` field (e.g. a row created
        # between the code deploy and the data migration running).
        return [self] if self.photo else []

    def to_snapshot(self, request=None):
        """Plain-dict representation safe to store on OrderItem at order
        creation time, so personalisation survives even if this row, its
        photos, or its parent CartItem are later deleted (e.g. cart
        clearing on payment). Always a list, even for a single photo -
        `photo_url` (singular) is kept alongside `photo_urls` purely so
        any older code/report reading the old key doesn't break."""

        def url_of(photo_like):
            image = photo_like.image if isinstance(photo_like, PersonalizationPhoto) else photo_like.photo
            if not image:
                return None
            return request.build_absolute_uri(image.url) if request else image.url

        photo_urls = [u for u in (url_of(p) for p in self.ordered_photos()) if u]

        return {
            "names": self.names,
            "date": self.date,
            "message": self.message,
            "style": self.style,
            "photo_url": photo_urls[0] if photo_urls else None,
            "photo_urls": photo_urls,
        }


class PersonalizationPhoto(models.Model):
    """
    One uploaded photo belonging to a Personalization, in customer-chosen
    order. Normalized one-to-many replacement for the old single `photo`
    field on Personalization, so a customer can attach multiple photos to
    one personalised cart line, add more later, and remove any one of
    them individually without touching the others.

    Deleting a row (individual photo removal, or cascade from removing a
    cart item/personalization) intentionally only ever deletes the DB
    row - never the physical file on disk. `to_snapshot()` freezes each
    photo's URL as a plain string onto OrderItem.personalization_snapshot
    at order-creation time, independent of this row's lifetime; an order
    can and does outlive its cart line (e.g. the cart is cleared once
    payment succeeds, but the order and its snapshot must keep displaying
    the customer's photos indefinitely). Physically deleting a file the
    moment its DB row goes away could silently 404 a real, already-placed
    order's photo. The tradeoff (some orphaned files accumulate on disk
    over time) is accepted deliberately in favour of never breaking a
    historical order; a scheduled cleanup job that cross-checks every
    OrderItem snapshot before removing a file would be the safe way to
    reclaim that space later, if it's ever needed.
    """

    personalization = models.ForeignKey(
        Personalization,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to=personalization_photo_upload_path)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"Photo #{self.pk} for personalization #{self.personalization_id}"
