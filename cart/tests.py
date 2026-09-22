from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Category, Product, ProductVariant
from personalization.models import Personalization, PersonalizationPhoto
from personalization.tests import make_image


class CartVariantTests(TestCase):
    """Covers the dynamic variant-pricing security requirements: a
    variant must belong to the product it's added against, must be
    active, and different variants of the same product must occupy
    separate cart lines rather than being merged together."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Test Frames", slug="frames-cart-test")
        self.frame = Product.objects.create(
            category=self.category,
            name="Test Frame",
            slug="test-frame",
            price=Decimal("699.00"),
            description="A test frame.",
            stock=10,
        )
        self.other_product = Product.objects.create(
            category=self.category,
            name="Other Product",
            slug="other-product",
            price=Decimal("899.00"),
            description="A different product.",
            stock=10,
        )
        self.small = ProductVariant.objects.create(
            product=self.frame, label="8x11 Inches", price=Decimal("799.00"), order=0,
        )
        self.large = ProductVariant.objects.create(
            product=self.frame, label="12x18 Inches", price=Decimal("1299.00"), order=1,
        )
        self.inactive = ProductVariant.objects.create(
            product=self.frame, label="Discontinued", price=Decimal("1.00"), order=2, is_active=False,
        )
        self.foreign_variant = ProductVariant.objects.create(
            product=self.other_product, label="Foreign Size", price=Decimal("50.00"), order=0,
        )
        self.guest_headers = {"HTTP_X_GUEST_ID": "test-guest-cart-variant"}

    def test_add_to_cart_with_valid_variant(self):
        res = self.client.post(
            "/api/cart/add/",
            {"product": self.frame.id, "variant": self.small.id, "quantity": 1},
            **self.guest_headers,
        )
        self.assertEqual(res.status_code, 201)

        items = self.client.get("/api/cart/items/", **self.guest_headers).json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["variant_id"], self.small.id)
        self.assertEqual(float(items[0]["product_price"]), 799.0)

    def test_different_variants_are_separate_cart_lines(self):
        self.client.post(
            "/api/cart/add/", {"product": self.frame.id, "variant": self.small.id, "quantity": 1}, **self.guest_headers,
        )
        self.client.post(
            "/api/cart/add/", {"product": self.frame.id, "variant": self.large.id, "quantity": 1}, **self.guest_headers,
        )
        items = self.client.get("/api/cart/items/", **self.guest_headers).json()
        self.assertEqual(len(items), 2)
        prices = sorted(float(i["product_price"]) for i in items)
        self.assertEqual(prices, [799.0, 1299.0])

    def test_same_variant_added_twice_merges_quantity(self):
        self.client.post(
            "/api/cart/add/", {"product": self.frame.id, "variant": self.small.id, "quantity": 1}, **self.guest_headers,
        )
        self.client.post(
            "/api/cart/add/", {"product": self.frame.id, "variant": self.small.id, "quantity": 2}, **self.guest_headers,
        )
        items = self.client.get("/api/cart/items/", **self.guest_headers).json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["quantity"], 3)

    def test_invalid_variant_id_rejected(self):
        res = self.client.post(
            "/api/cart/add/", {"product": self.frame.id, "variant": 999999, "quantity": 1}, **self.guest_headers,
        )
        self.assertEqual(res.status_code, 400)

    def test_cross_product_variant_rejected(self):
        res = self.client.post(
            "/api/cart/add/",
            {"product": self.frame.id, "variant": self.foreign_variant.id, "quantity": 1},
            **self.guest_headers,
        )
        self.assertEqual(res.status_code, 400)

    def test_inactive_variant_rejected(self):
        res = self.client.post(
            "/api/cart/add/", {"product": self.frame.id, "variant": self.inactive.id, "quantity": 1}, **self.guest_headers,
        )
        self.assertEqual(res.status_code, 400)

    def test_product_without_variant_still_works(self):
        res = self.client.post(
            "/api/cart/add/", {"product": self.other_product.id, "quantity": 1}, **self.guest_headers,
        )
        self.assertEqual(res.status_code, 201)
        items = self.client.get("/api/cart/items/", **self.guest_headers).json()
        self.assertIsNone(items[0]["variant_id"])
        self.assertEqual(float(items[0]["product_price"]), 899.0)


class CartPersonalizationSerializationTests(TestCase):
    """Covers the actual gap behind the reported issue: the cart API
    only ever told the frontend HOW MANY photos existed
    (personalization_photo_count), never the photos themselves - so
    Cart/Mini Cart/Checkout had no way to render real thumbnails at all,
    regardless of what Admin displayed."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Test Frames", slug="frames-cart-personalization-test")
        self.product = Product.objects.create(
            category=self.category, name="Cart Personalization Frame", slug="cart-personalization-frame",
            price=Decimal("699.00"), description="Test.", stock=10,
        )
        self.guest_headers = {"HTTP_X_GUEST_ID": "test-guest-cart-personalization"}

    def _add_and_get_item(self):
        self.client.post("/api/cart/add/", {"product": self.product.id, "quantity": 1}, **self.guest_headers)
        items = self.client.get("/api/cart/items/", **self.guest_headers).json()
        return items[0]

    def test_cart_item_without_personalization_has_null_field(self):
        item = self._add_and_get_item()
        self.assertIsNone(item["personalization"])
        self.assertEqual(item["personalization_photo_count"], 0)

    def test_cart_item_with_one_photo_returns_real_photo_url(self):
        from cart.models import CartItem
        item = self._add_and_get_item()
        cart_item = CartItem.objects.get(pk=item["id"])
        personalization = Personalization.objects.create(cart_item=cart_item, names="Solo Test")
        PersonalizationPhoto.objects.create(personalization=personalization, image=make_image("a.jpg"), display_order=0)

        item = self._add_and_get_item()
        self.assertIsNotNone(item["personalization"])
        self.assertEqual(item["personalization"]["names"], "Solo Test")
        self.assertEqual(len(item["personalization"]["photos"]), 1)
        self.assertTrue("/media/personalizations/" in item["personalization"]["photos"][0]["image"])

    def test_cart_item_with_multiple_photos_returns_all_in_order(self):
        from cart.models import CartItem
        item = self._add_and_get_item()
        cart_item = CartItem.objects.get(pk=item["id"])
        personalization = Personalization.objects.create(
            cart_item=cart_item, names="Multi Test", style="Elegant", message="Hi", date="2020",
        )
        for i, name in enumerate(["a.jpg", "b.jpg", "c.jpg", "d.jpg"]):
            PersonalizationPhoto.objects.create(personalization=personalization, image=make_image(name), display_order=i)

        item = self._add_and_get_item()
        photos = item["personalization"]["photos"]
        self.assertEqual(len(photos), 4)
        self.assertEqual([p["display_order"] for p in photos], [0, 1, 2, 3])
        self.assertEqual(item["personalization"]["style"], "Elegant")
        self.assertEqual(item["personalization"]["message"], "Hi")

    def test_cart_item_with_legacy_single_photo_field_still_serializes(self):
        """A pre-multi-photo personalisation (only the deprecated `photo`
        field populated, no PersonalizationPhoto rows) must not crash the
        cart API and must still expose that legacy photo."""
        from cart.models import CartItem
        item = self._add_and_get_item()
        cart_item = CartItem.objects.get(pk=item["id"])
        Personalization.objects.create(cart_item=cart_item, names="Legacy Test", photo=make_image("legacy.jpg"))

        item = self._add_and_get_item()
        self.assertIsNotNone(item["personalization"])
        self.assertEqual(item["personalization"]["names"], "Legacy Test")
        self.assertEqual(len(item["personalization"]["photos"]), 0)
        self.assertTrue("/media/personalizations/" in item["personalization"]["photo"])
