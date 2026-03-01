# cart/utils.py

from cart.models import Cart, CartItem


# ============================================
# GET CART FUNCTION
# ============================================

def get_cart(user=None, guest_id=None, create=False):
    """
    Cart Rules:
    - One cart per user
    - One cart per guest
    - Orders never block cart
    - Empty cart is valid
    """

    # ✅ AUTHENTICATED USER
    if user and user.is_authenticated:
        if create:
            cart, _ = Cart.objects.get_or_create(user=user)
            return cart

        return Cart.objects.filter(user=user).first()

    # ✅ GUEST USER
    if guest_id:
        if create:
            cart, _ = Cart.objects.get_or_create(guest_id=guest_id)
            return cart

        return Cart.objects.filter(guest_id=guest_id).first()

    return None


# ============================================
# MERGE GUEST CART INTO USER CART
# ============================================

def merge_guest_cart_to_user(guest_id, user):
    """
    When user logs in:
    - Merge guest cart into user cart
    - Combine quantities
    - Delete guest cart
    """

    if not guest_id or not user:
        return

    guest_cart = Cart.objects.filter(guest_id=guest_id).first()
    if not guest_cart:
        return

    # Ensure user has only one cart
    user_cart, _ = Cart.objects.get_or_create(user=user)

    for item in guest_cart.items.all():
        user_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            product=item.product,
            defaults={"quantity": item.quantity},
        )

        if not created:
            user_item.quantity += item.quantity
            user_item.save()

    # 🔥 Delete guest cart after successful merge
    guest_cart.delete()