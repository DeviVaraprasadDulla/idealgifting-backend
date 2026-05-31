from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.generics import ListAPIView
from django.db.models import F

from cart.models import CartItem
from cart.serializers import CartItemSerializer
from cart.utils import get_cart
from products.models import Product


# =============================
# ADD TO CART
# =============================
class AddToCartAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        product_id = request.data.get("product")
        quantity = request.data.get("quantity", 1)

        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                return Response({"error": "Invalid quantity"}, status=400)
        except:
            return Response({"error": "Invalid quantity"}, status=400)

        if not product_id:
            return Response({"error": "Product is required"}, status=400)

        try:
            product = Product.objects.get(pk=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)

        # Stock validation
        if product.stock < quantity:
            return Response({"error": "Not enough stock"}, status=400)

        cart = get_cart(
            user=request.user,
            guest_id=request.headers.get("X-GUEST-ID"),
            create=True
        )

        if not cart:
            return Response({"error": "Cart error"}, status=400)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity}
        )

        if not created:
            new_quantity = item.quantity + quantity

            if product.stock < new_quantity:
                return Response({"error": "Stock exceeded"}, status=400)

            item.quantity = new_quantity
            item.save()

        return Response({"message": "Item added"}, status=201)


# =============================
# LIST CART ITEMS
# =============================
class CartItemListAPIView(ListAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        cart = get_cart(
            user=self.request.user,
            guest_id=self.request.headers.get("X-GUEST-ID")
        )

        if not cart:
            return CartItem.objects.none()

        return CartItem.objects.filter(cart=cart).select_related("product")

    # 🔥 Important for image absolute URL
    def get_serializer_context(self):
        return {"request": self.request}


# =============================
# UPDATE CART ITEM
# =============================
class UpdateCartItemAPIView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, pk):
        quantity = request.data.get("quantity")

        try:
            quantity = int(quantity)
        except:
            return Response({"error": "Invalid quantity"}, status=400)

        cart = get_cart(
            user=request.user,
            guest_id=request.headers.get("X-GUEST-ID")
        )

        if not cart:
            return Response({"error": "Cart not found"}, status=404)

        try:
            item = CartItem.objects.select_related("product").get(pk=pk, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)

        # If quantity 0 → remove item
        if quantity <= 0:
            item.delete()
            return Response({"message": "Item removed"})

        # Stock validation
        if item.product.stock < quantity:
            return Response({"error": "Stock exceeded"}, status=400)

        item.quantity = quantity
        item.save()

        return Response({"message": "Quantity updated"})


# =============================
# REMOVE CART ITEM
# =============================
class RemoveCartItemAPIView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        cart = get_cart(
            user=request.user,
            guest_id=request.headers.get("X-GUEST-ID")
        )

        if not cart:
            return Response({"error": "Cart not found"}, status=404)

        try:
            item = CartItem.objects.get(pk=pk, cart=cart)
            item.delete()
            return Response({"message": "Item removed"})
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)


# =============================
# CHECKOUT (USER ONLY)
# =============================
class CheckoutAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):

        # 🔒 Only logged-in users
        if not request.user.is_authenticated:
            return Response({"error": "Login required"}, status=401)

        cart = get_cart(user=request.user)

        if not cart:
            return Response({"items": [], "total_amount": 0})

        items = CartItem.objects.select_related("product").filter(cart=cart)

        total = 0
        data = []

        for item in items:

            # Validate stock before checkout
            if item.product.stock < item.quantity:
                return Response(
                    {"error": f"{item.product.name} out of stock"},
                    status=400
                )

            discounted_price = item.product.price

            if item.product.discount_percentage > 0:
                discounted_price = (
                    item.product.price
                    - (item.product.price * item.product.discount_percentage / 100)
                )

            subtotal = discounted_price * item.quantity
            total += subtotal

            data.append({
                "product_id": item.product.id,
                "product": item.product.name,
                "price": discounted_price,
                "original_price": item.product.price,
                "discount_percentage": item.product.discount_percentage,
                "quantity": item.quantity,
                "subtotal": subtotal
            })

        return Response({
            "items": data,
            "total_amount": total
        })
