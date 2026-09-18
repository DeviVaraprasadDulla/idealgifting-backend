from django.contrib import admin
from django.db.models import Count
from .models import Personalization, PersonalizationPhoto


class PersonalizationPhotoInline(admin.TabularInline):
    model = PersonalizationPhoto
    extra = 0
    fields = ["image", "display_order"]
    readonly_fields = ["created_at"]


@admin.register(Personalization)
class PersonalizationAdmin(admin.ModelAdmin):
    list_display = ["cart_item", "names", "style", "photo_count", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PersonalizationPhotoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_photo_count=Count("photos"))

    def photo_count(self, obj):
        return obj._photo_count
    photo_count.short_description = "Photos"
    photo_count.admin_order_field = "_photo_count"
