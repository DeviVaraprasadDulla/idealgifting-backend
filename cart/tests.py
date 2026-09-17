from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Category, Product, ProductVariant


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
