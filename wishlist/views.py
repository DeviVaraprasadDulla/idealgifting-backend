from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from products.models import Product
from .models import Wishlist, WishlistItem
from .serializers import WishlistItemSerializer


def get_or_create_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


# =====================================================
# LIST + ADD
# =====================================================

class WishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist = get_or_create_wishlist(request.user)
        items = wishlist.items.select_related("product").prefetch_related(
            "product__images", "product__reviews"
        )
        serializer = WishlistItemSerializer(
            items, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        product_id = request.data.get("product")

        if not product_id:
            return Response(
                {"error": "product is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id, is_active=True)
        wishlist = get_or_create_wishlist(request.user)

        item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist, product=product
        )

        if not created:
            return Response(
                {"message": "Already in wishlist"}, status=status.HTTP_200_OK
            )

        serializer = WishlistItemSerializer(item, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# =====================================================
# REMOVE (by product id)
# =====================================================

class WishlistRemoveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id):
        wishlist = get_or_create_wishlist(request.user)
        deleted, _ = WishlistItem.objects.filter(
            wishlist=wishlist, product_id=product_id
        ).delete()

        if not deleted:
            return Response(
                {"error": "Not in wishlist"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response({"message": "Removed from wishlist"})


# =====================================================
# TOGGLE
# =====================================================

class WishlistToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product")

        if not product_id:
            return Response(
                {"error": "product is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id, is_active=True)
        wishlist = get_or_create_wishlist(request.user)

        item = WishlistItem.objects.filter(wishlist=wishlist, product=product).first()

        if item:
            item.delete()
            return Response({"wishlisted": False})

        WishlistItem.objects.create(wishlist=wishlist, product=product)
        return Response({"wishlisted": True})
