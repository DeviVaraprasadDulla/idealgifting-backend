from django.contrib import admin
from .models import Personalization


@admin.register(Personalization)
class PersonalizationAdmin(admin.ModelAdmin):
    list_display = ["cart_item", "names", "style", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
