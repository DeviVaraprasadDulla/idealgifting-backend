from rest_framework import serializers
from .models import Personalization

MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class PersonalizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personalization
        fields = ["id", "cart_item", "names", "date", "message", "style", "photo"]
        read_only_fields = ["id", "cart_item"]

    def validate_photo(self, photo):
        if photo is None:
            return photo

        if photo.size > MAX_PHOTO_SIZE_BYTES:
            raise serializers.ValidationError("Photo must be 5MB or smaller.")

        content_type = getattr(photo, "content_type", None)
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise serializers.ValidationError(
                "Photo must be a JPEG, PNG, or WEBP image."
            )

        return photo

    def validate_message(self, message):
        if len(message) > 300:
            raise serializers.ValidationError("Message must be 300 characters or fewer.")
        return message
