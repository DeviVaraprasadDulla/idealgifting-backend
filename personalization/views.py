from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from cart.models import CartItem
from cart.utils import get_cart
from .models import Personalization, PersonalizationPhoto
from .serializers import (
    PersonalizationSerializer,
    MAX_PHOTOS_PER_PERSONALIZATION,
    validate_photo_file,
)


def resolve_cart_item(request, cart_item_id):
    """Only ever return a cart item that belongs to the requester's own
    (guest or authenticated) cart - mirrors the existing cart app's
    guest/user resolution exactly, so personalization can't be attached
    to, read from, or modified on someone else's cart line no matter
    what id is requested."""
    cart = get_cart(
        user=request.user,
        guest_id=request.headers.get("X-GUEST-ID"),
    )
    if not cart:
        return None
    return CartItem.objects.filter(pk=cart_item_id, cart=cart).first()


class CartItemPersonalizationAPIView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, cart_item_id):
        cart_item = resolve_cart_item(request, cart_item_id)
        if not cart_item:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

        personalization = getattr(cart_item, "personalization", None)
        if not personalization:
            return Response(None)

        return Response(
            PersonalizationSerializer(personalization, context={"request": request}).data
        )

    def post(self, request, cart_item_id):
        """Create or update the personalization's text fields, and/or
        append any newly uploaded photos. Existing photos are never
        touched by this call - removing one is a separate, dedicated
        request (DELETE .../photos/<photo_id>/) so the customer never
        has to resend every photo just to add or remove one."""
        cart_item = resolve_cart_item(request, cart_item_id)
        if not cart_item:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

        instance = getattr(cart_item, "personalization", None)

        # Validate the whole photo batch BEFORE touching the database at
        # all - a rejected upload (bad type, too large, over the count
        # ceiling) must leave zero trace: no stray empty Personalization
        # row from a first-ever POST, no half-applied text-field save.
        new_files = request.FILES.getlist("photos")
        if new_files:
            existing_count = instance.photos.count() if instance else 0
            if existing_count + len(new_files) > MAX_PHOTOS_PER_PERSONALIZATION:
                return Response(
                    {
                        "error": (
                            f"You can attach up to {MAX_PHOTOS_PER_PERSONALIZATION} photos "
                            "to one gift. Please remove a photo before adding more."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for photo in new_files:
                try:
                    validate_photo_file(photo)
                except Exception as exc:
                    return Response({"error": str(exc.detail[0]) if hasattr(exc, "detail") else str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PersonalizationSerializer(
            instance=instance, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        personalization = serializer.save(cart_item=cart_item)

        if new_files:
            next_order = (
                personalization.photos.aggregate(m=Max("display_order"))["m"]
            )
            next_order = 0 if next_order is None else next_order + 1

            for i, photo in enumerate(new_files):
                PersonalizationPhoto.objects.create(
                    personalization=personalization,
                    image=photo,
                    display_order=next_order + i,
                )

        personalization.refresh_from_db()
        return Response(
            PersonalizationSerializer(personalization, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, cart_item_id):
        cart_item = resolve_cart_item(request, cart_item_id)
        if not cart_item:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

        Personalization.objects.filter(cart_item=cart_item).delete()
        return Response({"message": "Personalization removed"})


class PersonalizationPhotoDetailAPIView(APIView):
    """Removes exactly one photo from a personalization, leaving every
    other photo (and the rest of the personalization) untouched. The
    photo id alone is never trusted - it must belong to a personalization
    whose cart item resolves to the requester's own cart, exactly like
    every other personalization operation."""

    permission_classes = [AllowAny]

    def delete(self, request, cart_item_id, photo_id):
        cart_item = resolve_cart_item(request, cart_item_id)
        if not cart_item:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

        personalization = getattr(cart_item, "personalization", None)
        if not personalization:
            return Response({"error": "Photo not found"}, status=status.HTTP_404_NOT_FOUND)

        photo = personalization.photos.filter(pk=photo_id).first()
        if not photo:
            return Response({"error": "Photo not found"}, status=status.HTTP_404_NOT_FOUND)

        photo.delete()

        personalization.refresh_from_db()
        return Response(
            PersonalizationSerializer(personalization, context={"request": request}).data
        )
