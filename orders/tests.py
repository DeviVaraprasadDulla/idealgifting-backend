from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from products.models import Category, Product, ProductVariant
from .models import Address, OrderItem


class OrderVariantPricingTests(TestCase):
    """The server must always recalculate the order total from the
    selected variant's real database price - never trust anything the
    client sends - and must snapshot the variant onto the OrderItem so
    historical orders stay stable if the variant is later changed."""

    def setUp(self):
        self.user = User.objects.create_user(username="order-variant-tester", password="testpass123")
        self.client = APIClient()
        access = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        self.address = Address.objects.create(
            user=self.user,
            first_name="Test",
            last_name="User",
            phone="9999999999",
            address_line1="123 Test Street",
            city="Hyderabad",
            state="Telangana",
            zip_code="500001",
        )

        self.category = Category.objects.create(name="Test Frames", slug="frames-order-test")
        self.frame = Product.objects.create(
            category=self.category,
            name="Order Test Frame",
            slug="order-test-frame",
            price=Decimal("699.00"),
            description="A test frame.",
            stock=10,
        )
        self.large = ProductVariant.objects.create(
            product=self.frame, label="12x18 Inches", price=Decimal("1299.00"), order=0,
        )

    def _add_to_cart(self, quantity=1):
        return self.client.post(
            "/api/cart/add/",
            {"product": self.frame.id, "variant": self.large.id, "quantity": quantity},
        )

    def test_order_total_uses_variant_price_not_product_price(self):
        self._add_to_cart(quantity=2)
        res = self.client.post("/api/orders/create/", {"address_id": self.address.id})
        self.assertEqual(res.status_code, 200)
        # 1299 * 2 = 2598, never the flat product price (699) x 2 = 1398
        self.assertEqual(Decimal(str(res.json()["total_amount"])), Decimal("2598.00"))

    def test_order_item_snapshots_variant(self):
        self._add_to_cart(quantity=1)
        self.client.post("/api/orders/create/", {"address_id": self.address.id})
        item = OrderItem.objects.filter(product=self.frame).latest("id")
        self.assertEqual(item.variant_snapshot["label"], "12x18 Inches")
        self.assertEqual(Decimal(item.variant_snapshot["price"]), Decimal("1299.00"))
        self.assertEqual(item.price, Decimal("1299.00"))

    def test_client_supplied_price_is_ignored(self):
        """Order creation has no price/amount field to tamper with at
        all - the server only ever reads variant.price from the
        database, so this documents that guarantee against regression."""
        self._add_to_cart(quantity=1)
        res = self.client.post(
            "/api/orders/create/",
            {"address_id": self.address.id, "total_amount": "1", "price": "1"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Decimal(str(res.json()["total_amount"])), Decimal("1299.00"))

    def test_historical_order_price_stable_after_variant_price_change(self):
        self._add_to_cart(quantity=1)
        self.client.post("/api/orders/create/", {"address_id": self.address.id})
        item = OrderItem.objects.filter(product=self.frame).latest("id")

        self.large.price = Decimal("5000.00")
        self.large.save()

        item.refresh_from_db()
        self.assertEqual(item.price, Decimal("1299.00"))
        self.assertEqual(Decimal(item.variant_snapshot["price"]), Decimal("1299.00"))
