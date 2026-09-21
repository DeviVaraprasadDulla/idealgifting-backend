import os
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Order, OrderItem, OrderStatusHistory


# ============================================
# SNAPSHOT RENDERING HELPERS
#
# OrderItem.product_image/variant_snapshot/personalization_snapshot are
# denormalized copies captured at order-creation time (see the model's
# own docstrings) - they are plain URLField/JSONField values, not live
# FK relations, so there is nothing to "resolve" from the DB beyond
# reading the stored value. Django's default widgets render a JSONField
# as a large editable <textarea> of raw JSON, and a URLField as a plain
# text input - neither ever shows an actual image. These helpers turn
# those stored values into compact, readonly, escaped HTML instead.
# ============================================

def _local_media_file_exists(url):
    """Best-effort existence check against this project's local
    filesystem storage (its only backend - see MEDIA_ROOT/MEDIA_URL in
    settings.py). Works for both a relative ("/media/x.jpg") and an
    absolute ("http://host/media/x.jpg") stored URL, since only the
    path portion is ever used to resolve a file. If the path doesn't
    look like it lives under MEDIA_URL at all, we don't claim it's
    missing - we just skip the check and let it render normally."""
    try:
        path = urlparse(url).path
    except ValueError:
        return True
    if not path.startswith(settings.MEDIA_URL):
        return True
    relative = path[len(settings.MEDIA_URL):]
    return os.path.exists(os.path.join(settings.MEDIA_ROOT, relative))


def _snapshot_image_preview(url, size=110):
    """Render one stored snapshot URL as a clickable thumbnail, or a
    clear "Image unavailable" placeholder if the underlying file is
    genuinely gone - never a bare broken-image icon, and never a raw
    path. The historical URL (relative or absolute, any host) is used
    exactly as stored for both the link and the <img src> - this only
    displays what order creation actually captured, it doesn't rewrite
    it."""
    if not url:
        return "—"
    if not _local_media_file_exists(url):
        return format_html(
            '<div style="width:{0}px; min-height:60px; display:flex; align-items:center; '
            'justify-content:center; background:#f5f5f5; border:1px dashed #ccc; '
            'border-radius:6px; color:#999; font-size:11px; text-align:center; padding:6px;">'
            "Image unavailable</div>",
            size,
        )
    return format_html(
        '<a href="{0}" target="_blank" rel="noopener noreferrer">'
        '<img src="{0}" alt="" style="max-width:{1}px; max-height:{1}px; object-fit:contain; '
        'border-radius:6px; border:1px solid #ddd; background:#fafafa; display:block;" />'
        "</a>",
        url,
        size,
    )


def _snapshot_meta_lines(snapshot):
    lines = []
    for key, label in [("names", "Names"), ("date", "Date"), ("message", "Message"), ("style", "Style")]:
        value = snapshot.get(key)
        if value:
            lines.append(format_html("<b>{}:</b> {}", label, value))
    return lines


# ============================================
# ORDER ITEM INLINE
# ============================================

class OrderItemInline(admin.StackedInline):
    # Deliberately a StackedInline, not TabularInline: a table row has a
    # fixed height and forces every field onto one horizontal line, which
    # is exactly what made this section oversized and horizontally
    # scrollable in the first place once multiple photo thumbnails and
    # personalization text needed to sit alongside product/variant/price.
    # A stacked layout lets each field take the full content width and
    # wrap/grow vertically instead, which is the actual fix - not a
    # scoped-down max-width or overflow-x: hidden band-aid.
    model = OrderItem
    extra = 0
    can_delete = False
    fields = (
        ("product", "product_name", "product_image_preview"),
        ("quantity", "price", "variant_display"),
        "personalization_display",
    )
    readonly_fields = (
        "product",
        "product_name",
        "product_image_preview",
        "price",
        "quantity",
        "variant_display",
        "personalization_display",
    )

    @admin.display(description="Product image")
    def product_image_preview(self, obj):
        return _snapshot_image_preview(obj.product_image, size=80)

    @admin.display(description="Variant")
    def variant_display(self, obj):
        snap = obj.variant_snapshot
        if not snap:
            return "—"
        label = snap.get("label")
        price = snap.get("price")
        if label and price:
            return format_html("{} — ₹{}", label, price)
        return label or "—"

    @admin.display(description="Personalization")
    def personalization_display(self, obj):
        snap = obj.personalization_snapshot
        if not snap:
            return "—"

        # Multi-photo orders store `photo_urls` (a list); a handful of
        # orders placed before multi-photo support existed only have the
        # single legacy `photo_url` key - fall back to that so an old
        # order's one photo still displays instead of nothing.
        photo_urls = snap.get("photo_urls")
        if not photo_urls and snap.get("photo_url"):
            photo_urls = [snap["photo_url"]]
        photo_urls = photo_urls or []

        thumbs_html = ""
        if photo_urls:
            thumbs = [
                format_html(
                    '<div style="display:inline-block; margin:0 8px 8px 0; text-align:center; '
                    'vertical-align:top;">{}<div style="font-size:10px; color:#888; margin-top:2px;">'
                    "Photo {}</div></div>",
                    _snapshot_image_preview(url),
                    i,
                )
                for i, url in enumerate(photo_urls, start=1)
            ]
            thumbs_html = format_html(
                '<div style="display:flex; flex-wrap:wrap; max-width:480px;">{}</div>',
                mark_safe("".join(thumbs)),
            )

        meta_lines = _snapshot_meta_lines(snap)
        meta_html = ""
        if meta_lines:
            meta_html = format_html(
                '<div style="margin-top:4px; font-size:12px; color:#444; max-width:480px;">{}</div>',
                mark_safe("<br>".join(meta_lines)),
            )

        if not thumbs_html and not meta_html:
            return "—"

        return format_html("{}{}", thumbs_html, meta_html)


# ============================================
# ORDER STATUS HISTORY INLINE
# ============================================

class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = (
        "status",
        "updated_at",
    )


# ============================================
# ORDER ADMIN
# ============================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "total_amount",
        "payment_status",
        "order_status",
        "tracking_id",
        "created_at",
    )

    list_filter = (
        "payment_status",
        "order_status",
        "created_at",
    )

    search_fields = (
        "id",
        "user__username",
        "user__email",
        "tracking_id",
    )

    readonly_fields = (
        "public_token",
        "created_at",
    )

    inlines = [
        OrderItemInline,
        OrderStatusHistoryInline,
    ]

    # ============================================
    # AUTO TIMELINE + AUTO SHIPPED DATE
    # ============================================

    def save_model(self, request, obj, form, change):

        if change:
            old_obj = Order.objects.get(pk=obj.pk)

            # If order_status changed
            if old_obj.order_status != obj.order_status:

                # Add timeline entry
                OrderStatusHistory.objects.create(
                    order=obj,
                    status=obj.order_status
                )

                # Auto set shipped_at
                if obj.order_status == "SHIPPED":
                    obj.shipped_at = timezone.now()

        super().save_model(request, obj, form, change)
