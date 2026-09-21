from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from .models import Personalization, PersonalizationPhoto


# Django's default AdminFileWidget only ever renders "Currently: <a
# href=...>path</a>" for an ImageField - never an actual <img>. These
# helpers render a real thumbnail instead, always via the field's own
# `.url` (which Django/the storage backend builds from MEDIA_URL) -
# never a hardcoded host, so it keeps working unchanged in any
# environment (dev, staging, behind a different domain, etc).
def _image_preview(image_field, size=120):
    if not image_field:
        return "No image"
    return format_html(
        '<a href="{0}" target="_blank" rel="noopener noreferrer">'
        '<img src="{0}" style="max-width:{1}px; max-height:{1}px; '
        'object-fit:cover; border-radius:6px; border:1px solid #ddd;" />'
        "</a>",
        image_field.url,
        size,
    )


class PersonalizationPhotoInline(admin.TabularInline):
    model = PersonalizationPhoto
    extra = 0
    fields = ["preview", "image", "display_order", "created_at"]
    readonly_fields = ["preview", "created_at"]

    @admin.display(description="Preview")
    def preview(self, obj):
        return _image_preview(obj.image)


@admin.register(Personalization)
class PersonalizationAdmin(admin.ModelAdmin):
    list_display = ["cart_item", "names", "style", "photo_count", "updated_at"]
    fields = [
        "cart_item", "names", "date", "message", "style",
        "photo", "legacy_photo_preview",
        "created_at", "updated_at",
    ]
    readonly_fields = ["legacy_photo_preview", "created_at", "updated_at"]
    inlines = [PersonalizationPhotoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_photo_count=Count("photos"))

    def photo_count(self, obj):
        return obj._photo_count
    photo_count.short_description = "Photos"
    photo_count.admin_order_field = "_photo_count"

    @admin.display(description="Legacy photo preview")
    def legacy_photo_preview(self, obj):
        # Only ever populated on pre-multi-photo records (see the `photo`
        # field's own docstring on the model) - shown here purely so an
        # old record's single photo remains visible, same as any of the
        # new PersonalizationPhoto rows below.
        return _image_preview(obj.photo)
