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

    Must match on (product, variant), not product alone - two guest
    lines for the same product with different sizes/page-counts are
    different purchases and must never be collapsed into one. Where no
    matching line already exists in the user's own cart (the common
    case), the guest CartItem row itself is re-parented onto the user's
    cart rather than recreated, so its personalisation (and every photo
    attached to it) - a real, distinct database row this row's own
    id - moves across intact with zero extra work.
    """

    if not guest_id or not user:
        return

    guest_cart = Cart.objects.filter(guest_id=guest_id).first()
    if not guest_cart:
        return

    # Ensure user has only one cart
    user_cart, _ = Cart.objects.get_or_create(user=user)

    for item in guest_cart.items.select_related("personalization").all():
        existing = CartItem.objects.filter(
            cart=user_cart, product=item.product, variant=item.variant
        ).first()

        if not existing:
            # No collision - move this exact row (and its
            # personalization/photos, via cart_item's FK) onto the
            # user's cart. Nothing to copy or lose.
            item.cart = user_cart
            item.save(update_fields=["cart"])
            continue

        # A line for the same product+variant already exists in the
        # user's own account cart. Combine quantities as before.
        existing.quantity += item.quantity
        existing.save(update_fields=["quantity"])

        # If the guest line was personalised and the existing account
        # line was not, carry the personalisation (and its photos)
        # across by re-pointing it at the surviving line, rather than
        # silently discarding real customer work.
        guest_personalization = getattr(item, "personalization", None)
        if guest_personalization and not hasattr(existing, "personalization"):
            guest_personalization.cart_item = existing
            guest_personalization.save(update_fields=["cart_item"])

        # The guest CartItem row itself is now redundant (its quantity
        # and any personalisation it uniquely held have both been
        # carried onto `existing`) - deleting it here, rather than via
        # the guest cart's own cascade below, avoids also cascading
        # away a personalization that was just re-pointed elsewhere.
        item.delete()

    # 🔥 Delete guest cart after successful merge
    guest_cart.delete()