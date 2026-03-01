from django.contrib import admin
from .models import SiteAnnouncement


@admin.register(SiteAnnouncement)
class SiteAnnouncementAdmin(admin.ModelAdmin):
    list_display = ("message", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("message",)
    ordering = ("-created_at",)
