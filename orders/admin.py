from django.contrib import admin
from django.utils import timezone
from .models import Order, OrderItem, OrderStatusHistory


# ============================================
# ORDER ITEM INLINE
# ============================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "product",
        "product_name",
        "price",
        "quantity",
    )


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