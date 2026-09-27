from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.test import Client as DjangoTestClient
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from products.models import Category, Product, ProductVariant
from .models import Address, Order, OrderItem


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


class OrderItemAdminPersonalizationDisplayTests(TestCase):
    """Covers the reported issue: Order Admin showed raw 'null'/JSON for
    personalization instead of the customer's actual uploaded photos.
    Exercises the Admin change page directly (not just the model/API),
    since the bug was entirely in how OrderItemInline rendered an
    already-correct snapshot value."""

    def setUp(self):
        self.staff = User.objects.create_user(
            username="order-admin-tester", password="testpass123", is_staff=True, is_superuser=True,
        )
        self.django_client = DjangoTestClient()
        self.django_client.force_login(self.staff)
        self.order = Order.objects.create(total_amount=Decimal("999.00"))
        self._saved_file_names = []

    def tearDown(self):
        from django.core.files.storage import default_storage
        for name in self._saved_file_names:
            default_storage.delete(name)

    def _change_url(self):
        return reverse("admin:orders_order_change", args=[self.order.id])

    def _real_media_url(self, relative_path, content=b"\xff\xd8\xff fake jpeg bytes"):
        """Writes an actual file under MEDIA_ROOT (via the real storage
        backend, cleaned up in tearDown) and returns its relative URL -
        for tests that need the "file genuinely exists" path, as opposed
        to test_missing_file_..., which deliberately references a path
        that was never written."""
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        saved_name = default_storage.save(relative_path, ContentFile(content))
        self._saved_file_names.append(saved_name)
        return default_storage.url(saved_name)

    def test_order_item_with_no_personalization_shows_dash_not_broken_image(self):
        OrderItem.objects.create(
            order=self.order, product_name="Plain Item", price=Decimal("499.00"), quantity=1,
            personalization_snapshot=None,
        )
        res = self.django_client.get(self._change_url())
        self.assertEqual(res.status_code, 200)
        content = res.content.decode()
        self.assertNotIn("Image unavailable", content)
        # The personalization column itself must render the plain "—"
        # placeholder, not any <img> tag (broken or otherwise). There
        # are two "field-personalization_display" occurrences per row
        # (the outer and inner wrapping divs) before the actual value,
        # so anchor on the field's unique label id instead.
        label_idx = content.find('for="id_personalization_display"')
        self.assertNotEqual(label_idx, -1, "personalization_display field not found on the page")
        personalization_cell = content[label_idx:label_idx + 600]
        self.assertNotIn("<img", personalization_cell)
        self.assertIn("—", personalization_cell)

    def test_order_item_with_one_photo_renders_exactly_one_img(self):
        url = self._real_media_url("personalizations/test-order-admin/a.jpg")
        OrderItem.objects.create(
            order=self.order, product_name="Framed Photo", price=Decimal("799.00"), quantity=1,
            personalization_snapshot={
                "names": "Test User", "date": "", "message": "", "style": "Classic",
                "photo_url": url, "photo_urls": [url],
            },
        )
        res = self.django_client.get(self._change_url())
        content = res.content.decode()
        self.assertIn(f'<img src="{url}"', content)
        self.assertEqual(content.count(f'src="{url}"'), 1)

    def test_order_item_with_multiple_photos_renders_every_image(self):
        urls = [self._real_media_url(f"personalizations/test-order-admin/p{i}.jpg") for i in range(4)]
        OrderItem.objects.create(
            order=self.order, product_name="Multi Photo Frame", price=Decimal("1299.00"), quantity=1,
            personalization_snapshot={
                "names": "Ananya & Karan", "date": "Since 2019", "message": "Hello",
                "style": "Elegant", "photo_url": urls[0], "photo_urls": urls,
            },
        )
        content = self.django_client.get(self._change_url()).content.decode()
        for url in urls:
            self.assertIn(f'<img src="{url}"', content)
        # Explicitly guards against "only the first photo displayed".
        self.assertEqual(content.count('style="font-size:10px; color:#888; margin-top:2px;"'), 4)

    def test_legacy_single_photo_format_still_renders(self):
        """Some real historical orders predate the `photo_urls` list key
        entirely and only ever had the old singular `photo_url` - this
        must still display, not just newer-format snapshots."""
        url = self._real_media_url("personalizations/test-order-admin/legacy-old.jpg")
        OrderItem.objects.create(
            order=self.order, product_name="Legacy Item", price=Decimal("699.00"), quantity=1,
            personalization_snapshot={
                "names": "Legacy Customer", "date": "", "message": "", "style": "",
                "photo_url": url,
                # deliberately no "photo_urls" key at all
            },
        )
        content = self.django_client.get(self._change_url()).content.decode()
        self.assertIn(f'<img src="{url}"', content)

    def test_missing_file_shows_graceful_fallback_not_broken_image(self):
        OrderItem.objects.create(
            order=self.order, product_name="Item With Deleted File", price=Decimal("699.00"), quantity=1,
            personalization_snapshot={
                "names": "Someone", "date": "", "message": "", "style": "",
                "photo_url": "/media/personalizations/does-not-exist-999999/gone.jpg",
                "photo_urls": ["/media/personalizations/does-not-exist-999999/gone.jpg"],
            },
        )
        res = self.django_client.get(self._change_url())
        self.assertEqual(res.status_code, 200)
        content = res.content.decode()
        self.assertIn("Image unavailable", content)
        self.assertNotIn('<img src="/media/personalizations/does-not-exist-999999/gone.jpg"', content)

    def test_absolute_url_in_snapshot_renders_correctly(self):
        """Real order snapshots store an absolute URL (built via
        request.build_absolute_uri at order-creation time) - must be
        used as-is, not mangled."""
        relative_url = self._real_media_url("personalizations/test-order-admin/abs.jpg")
        absolute_url = f"http://testserver{relative_url}"
        OrderItem.objects.create(
            order=self.order, product_name="Absolute URL Item", price=Decimal("699.00"), quantity=1,
            personalization_snapshot={
                "names": "", "date": "", "message": "", "style": "",
                "photo_url": absolute_url,
                "photo_urls": [absolute_url],
            },
        )
        content = self.django_client.get(self._change_url()).content.decode()
        self.assertIn(f'<img src="{absolute_url}"', content)

    def test_relative_url_in_snapshot_renders_correctly(self):
        url = self._real_media_url("personalizations/test-order-admin/rel.jpg")
        OrderItem.objects.create(
            order=self.order, product_name="Relative URL Item", price=Decimal("699.00"), quantity=1,
            personalization_snapshot={
                "names": "", "date": "", "message": "", "style": "",
                "photo_url": url,
                "photo_urls": [url],
            },
        )
        content = self.django_client.get(self._change_url()).content.decode()
        self.assertIn(f'<img src="{url}"', content)

    def test_personalization_text_fields_are_html_escaped(self):
        """A malicious or accidental <script>/HTML value typed into
        names/message must never be rendered unescaped in Admin."""
        OrderItem.objects.create(
            order=self.order, product_name="XSS Test Item", price=Decimal("699.00"), quantity=1,
            personalization_snapshot={
                "names": "<script>alert(1)</script>",
                "date": "", "message": "<img src=x onerror=alert(2)>", "style": "",
                "photo_url": None,
            },
        )
        content = self.django_client.get(self._change_url()).content.decode()
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertNotIn("<img src=x onerror=alert(2)>", content)

    def test_variant_snapshot_renders_as_readable_text_not_raw_json(self):
        OrderItem.objects.create(
            order=self.order, product_name="Variant Item", price=Decimal("1299.00"), quantity=1,
            variant_snapshot={"id": 1, "label": "12x18 Inches", "price": "1299.00"},
        )
        content = self.django_client.get(self._change_url()).content.decode()
        self.assertIn("12x18 Inches", content)
        self.assertIn("1299.00", content)


class OrderCustomerAPIPersonalizationTests(TestCase):
    """Covers the customer-facing side of the same requirement: My
    Orders and Order Details must actually receive photo references from
    the API (the frontend renders whatever these endpoints return - if
    the API omits photo_urls, no amount of frontend work can show them)."""

    def setUp(self):
        self.user = User.objects.create_user(username="order-api-tester", password="testpass123")
        self.client = APIClient()
        access = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.order = Order.objects.create(user=self.user, total_amount=Decimal("1299.00"), payment_status="PAID")

    def test_my_orders_includes_personalization_photo_urls(self):
        OrderItem.objects.create(
            order=self.order, product_name="Love Story Frame", price=Decimal("1299.00"), quantity=1,
            personalization_snapshot={
                "names": "John & Jane", "date": "2020", "message": "Hi", "style": "Elegant",
                "photo_url": "/media/personalizations/1/a.jpg",
                "photo_urls": ["/media/personalizations/1/a.jpg", "/media/personalizations/1/b.jpg"],
            },
        )
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        order = next(o for o in data if o["id"] == self.order.id)
        item = order["items"][0]
        self.assertEqual(item["personalization"]["names"], "John & Jane")
        self.assertEqual(len(item["personalization"]["photo_urls"]), 2)

    def test_order_by_token_includes_personalization_photo_urls(self):
        OrderItem.objects.create(
            order=self.order, product_name="Love Story Frame", price=Decimal("1299.00"), quantity=1,
            personalization_snapshot={
                "names": "John & Jane", "date": "2020", "message": "Hi", "style": "Elegant",
                "photo_url": "/media/personalizations/1/a.jpg",
                "photo_urls": ["/media/personalizations/1/a.jpg", "/media/personalizations/1/b.jpg"],
            },
        )
        res = self.client.get(f"/api/orders/by-token/{self.order.public_token}/")
        self.assertEqual(res.status_code, 200)
        item = res.json()["items"][0]
        self.assertEqual(len(item["personalization"]["photo_urls"]), 2)

    def test_order_with_no_personalization_returns_null_not_error(self):
        OrderItem.objects.create(
            order=self.order, product_name="Plain Item", price=Decimal("499.00"), quantity=1,
        )
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, 200)
        item = res.json()[0]["items"][0]
        self.assertIsNone(item["personalization"])

    def test_order_with_legacy_photo_url_only_still_returns_it(self):
        OrderItem.objects.create(
            order=self.order, product_name="Legacy Item", price=Decimal("499.00"), quantity=1,
            personalization_snapshot={
                "names": "Legacy Customer", "date": "", "message": "", "style": "",
                "photo_url": "/media/personalizations/legacy/old.jpg",
                # deliberately no photo_urls key, matching pre-multi-photo orders
            },
        )
        res = self.client.get("/api/orders/")
        item = res.json()[0]["items"][0]
        self.assertEqual(item["personalization"]["photo_url"], "/media/personalizations/legacy/old.jpg")
