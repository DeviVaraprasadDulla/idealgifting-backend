from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from cart.models import CartItem
from cart.utils import get_cart
from .models import Personalization
from .serializers import PersonalizationSerializer


def resolve_cart_item(request, cart_item_id):
    """Only ever return a cart item that belongs to the requester's own
    (guest or authenticated) cart - mirrors the existing cart app's
    guest/user resolution exactly, so personalization can't be attached
    to someone else's cart line."""
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
        cart_item = resolve_cart_item(request, cart_item_id)
        if not cart_item:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

        instance = getattr(cart_item, "personalization", None)
        serializer = PersonalizationSerializer(
            instance=instance, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(cart_item=cart_item)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, cart_item_id):
        cart_item = resolve_cart_item(request, cart_item_id)
        if not cart_item:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

        Personalization.objects.filter(cart_item=cart_item).delete()
        return Response({"message": "Personalization removed"})
