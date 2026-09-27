from rest_framework import serializers
from .models import Personalization, PersonalizationPhoto

MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

# No business-defined maximum number of photos exists anywhere in the
# current application (the previous version only ever supported exactly
# one). This is a generous, configurable abuse-prevention ceiling, not a
# product rule - real personalisation only ever needs a handful of
# photos, but nothing customer-facing should ever describe this number
# as a deliberate limit. Override via the PERSONALIZATION_MAX_PHOTOS
# Django setting if a real limit is ever required.
from django.conf import settings

MAX_PHOTOS_PER_PERSONALIZATION = getattr(settings, "PERSONALIZATION_MAX_PHOTOS", 20)


def validate_photo_file(photo):
    if photo.size > MAX_PHOTO_SIZE_BYTES:
        raise serializers.ValidationError(
            f'"{photo.name}" is larger than 5MB. Please choose a smaller photo.'
        )

    content_type = getattr(photo, "content_type", None)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise serializers.ValidationError(
            f'"{photo.name}" could not be uploaded. Please choose a JPEG, PNG, or WEBP image.'
        )


class PersonalizationPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalizationPhoto
        fields = ["id", "image", "display_order"]


class PersonalizationSerializer(serializers.ModelSerializer):
    photos = PersonalizationPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Personalization
        fields = ["id", "cart_item", "names", "date", "message", "style", "photo", "photos"]
        read_only_fields = ["id", "cart_item", "photo", "photos"]

    def validate_message(self, message):
        if len(message) > 300:
            raise serializers.ValidationError("Message must be 300 characters or fewer.")
        return message
