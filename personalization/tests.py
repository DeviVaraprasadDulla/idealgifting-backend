import io
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import Client as DjangoTestClient
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cart.models import Cart, CartItem
from cart.utils import merge_guest_cart_to_user
from products.models import Category, Product, ProductVariant
from .models import Personalization, PersonalizationPhoto


def make_image(name="photo.jpg", color=(255, 0, 0), fmt="JPEG", size_kb=None):
    """A real, valid, tiny in-memory JPEG/PNG for upload tests - not a
    fake/empty file, so validation genuinely exercises Pillow's decode
    path the same way a real customer photo would."""
    buf = io.BytesIO()
    img = Image.new("RGB", (50, 50), color)
    img.save(buf, format=fmt)
    content = buf.getvalue()
    if size_kb:
        content += b"\0" * (size_kb * 1024 - len(content))
    content_type = "image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}"
    return SimpleUploadedFile(name, content, content_type=content_type)


class PersonalizationMultiPhotoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Test Frames", slug="frames-personalization-test")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Personalization Frame",
            slug="test-personalization-frame",
            price=Decimal("699.00"),
            description="A test frame.",
            stock=10,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, label="12x18 Inches", price=Decimal("1299.00"), order=0,
        )
        self.other_product = Product.objects.create(
            category=self.category,
            name="Other Test Product",
            slug="other-test-product-personalization",
            price=Decimal("499.00"),
            description="A different product.",
            stock=10,
        )
        self.guest_headers = {"HTTP_X_GUEST_ID": "test-guest-personalization"}

    def _add_to_cart(self, product=None, variant=None, headers=None, quantity=1):
        headers = headers or self.guest_headers
        product = product or self.product
        payload = {"product": product.id, "quantity": quantity}
        if variant:
            payload["variant"] = variant.id
        self.client.post("/api/cart/add/", payload, **headers)
        items = self.client.get("/api/cart/items/", **headers).json()
        expected_variant_id = variant.id if variant else None
        return next(
            i for i in items
            if i["product_id"] == product.id and i["variant_id"] == expected_variant_id
        )["id"]

    # ---------------- one photo (baseline, still works) ----------------

    def test_upload_single_photo(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"names": "Ananya & Karan", "photos": [make_image()]},
            format="multipart",
            **self.guest_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["photos"]), 1)
        self.assertEqual(data["photos"][0]["display_order"], 0)

    # ---------------- multiple photos ----------------

    def test_upload_multiple_photos_at_once(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {
                "names": "Ananya & Karan",
                "photos": [make_image("a.jpg"), make_image("b.jpg"), make_image("c.jpg"), make_image("d.jpg")],
            },
            format="multipart",
            **self.guest_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["photos"]), 4)
        self.assertEqual([p["display_order"] for p in data["photos"]], [0, 1, 2, 3])

    def test_add_more_photos_progressively(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [make_image("a.jpg"), make_image("b.jpg")]},
            format="multipart",
            **self.guest_headers,
        )
        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [make_image("c.jpg")]},
            format="multipart",
            **self.guest_headers,
        )
        data = res.json()
        self.assertEqual(len(data["photos"]), 3)
        # newly added photo continues the order sequence rather than
        # restarting at 0 and colliding with existing photos
        self.assertEqual(data["photos"][-1]["display_order"], 2)

    def test_remove_one_photo_leaves_others_intact(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [make_image("a.jpg"), make_image("b.jpg"), make_image("c.jpg")]},
            format="multipart",
            **self.guest_headers,
        )
        photo_ids = [p["id"] for p in res.json()["photos"]]
        self.assertEqual(len(photo_ids), 3)

        middle_id = photo_ids[1]
        res2 = self.client.delete(
            f"/api/personalization/cart-item/{cart_item_id}/photos/{middle_id}/",
            **self.guest_headers,
        )
        self.assertEqual(res2.status_code, 200)
        remaining_ids = [p["id"] for p in res2.json()["photos"]]
        self.assertEqual(len(remaining_ids), 2)
        self.assertNotIn(middle_id, remaining_ids)
        self.assertIn(photo_ids[0], remaining_ids)
        self.assertIn(photo_ids[2], remaining_ids)

    def test_order_preserved_across_add_remove_and_refetch(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [make_image("a.jpg"), make_image("b.jpg"), make_image("c.jpg")]},
            format="multipart",
            **self.guest_headers,
        )
        get_res = self.client.get(f"/api/personalization/cart-item/{cart_item_id}/", **self.guest_headers)
        orders = [p["display_order"] for p in get_res.json()["photos"]]
        self.assertEqual(orders, sorted(orders))

    # ---------------- validation ----------------

    def test_invalid_file_type_rejected_with_clear_message(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        bad_file = SimpleUploadedFile("not-an-image.txt", b"hello world", content_type="text/plain")
        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [bad_file]},
            format="multipart",
            **self.guest_headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())
        self.assertNotIn("Traceback", res.json()["error"])

    def test_oversized_photo_rejected(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        big_file = make_image("big.jpg", size_kb=6 * 1024)  # 6MB, over the 5MB limit
        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [big_file]},
            format="multipart",
            **self.guest_headers,
        )
        self.assertEqual(res.status_code, 400)

    def test_oversized_photo_in_a_batch_rejects_whole_batch(self):
        """A mixed batch with one bad file fails the request rather than
        silently saving only the valid ones - the customer sees exactly
        what needs fixing instead of a partially-applied upload."""
        cart_item_id = self._add_to_cart(variant=self.variant)
        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [make_image("good.jpg"), make_image("big.jpg", size_kb=6 * 1024)]},
            format="multipart",
            **self.guest_headers,
        )
        self.assertEqual(res.status_code, 400)
        get_res = self.client.get(f"/api/personalization/cart-item/{cart_item_id}/", **self.guest_headers)
        # No personalization was created at all - the existing "nothing
        # here yet" response shape (200, empty body) rather than JSON null.
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.content, b"")

    # ---------------- security ----------------

    def test_cannot_view_another_guests_personalization(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [make_image()]},
            format="multipart",
            **self.guest_headers,
        )
        res = self.client.get(
            f"/api/personalization/cart-item/{cart_item_id}/",
            HTTP_X_GUEST_ID="a-completely-different-guest",
        )
        self.assertEqual(res.status_code, 404)

    def test_cannot_delete_photo_via_another_guests_cart_item(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [make_image()]},
            format="multipart",
            **self.guest_headers,
        )
        photo_id = res.json()["photos"][0]["id"]
        res2 = self.client.delete(
            f"/api/personalization/cart-item/{cart_item_id}/photos/{photo_id}/",
            HTTP_X_GUEST_ID="a-completely-different-guest",
        )
        self.assertEqual(res2.status_code, 404)
        # the photo must genuinely still exist, untouched
        self.assertTrue(PersonalizationPhoto.objects.filter(pk=photo_id).exists())

    def test_cannot_delete_photo_belonging_to_a_different_cart_item(self):
        """Even the SAME guest cannot delete a photo by quoting the
        right photo id against the wrong cart_item_id in the URL."""
        cart_item_1 = self._add_to_cart(product=self.product, variant=self.variant)
        cart_item_2 = self._add_to_cart(product=self.other_product)

        res = self.client.post(
            f"/api/personalization/cart-item/{cart_item_1}/",
            {"photos": [make_image()]},
            format="multipart",
            **self.guest_headers,
        )
        photo_id = res.json()["photos"][0]["id"]

        res2 = self.client.delete(
            f"/api/personalization/cart-item/{cart_item_2}/photos/{photo_id}/",
            **self.guest_headers,
        )
        self.assertEqual(res2.status_code, 404)
        self.assertTrue(PersonalizationPhoto.objects.filter(pk=photo_id).exists())

    # ---------------- variant association ----------------

    def test_personalization_stays_attached_to_correct_variant_line(self):
        small = ProductVariant.objects.create(
            product=self.product, label="8x11 Inches", price=Decimal("799.00"), order=1,
        )
        item_large = self._add_to_cart(variant=self.variant)
        item_small = self._add_to_cart(variant=small)
        self.assertNotEqual(item_large, item_small)

        self.client.post(
            f"/api/personalization/cart-item/{item_large}/",
            {"names": "Large photo set", "photos": [make_image("a.jpg"), make_image("b.jpg")]},
            format="multipart",
            **self.guest_headers,
        )
        self.client.post(
            f"/api/personalization/cart-item/{item_small}/",
            {"names": "Small photo set", "photos": [make_image("c.jpg")]},
            format="multipart",
            **self.guest_headers,
        )

        items = self.client.get("/api/cart/items/", **self.guest_headers).json()
        large_item = next(i for i in items if i["id"] == item_large)
        small_item = next(i for i in items if i["id"] == item_small)
        self.assertEqual(large_item["variant_label"], "12x18 Inches")
        self.assertEqual(large_item["personalization_photo_count"], 2)
        self.assertEqual(small_item["variant_label"], "8x11 Inches")
        self.assertEqual(small_item["personalization_photo_count"], 1)

    # ---------------- backwards compatibility ----------------

    def test_legacy_single_photo_field_still_reads_correctly(self):
        cart_item_id = self._add_to_cart(variant=self.variant)
        cart_item = CartItem.objects.get(pk=cart_item_id)
        legacy = Personalization.objects.create(
            cart_item=cart_item,
            names="Old Customer",
            photo=make_image("legacy.jpg"),
        )
        # No PersonalizationPhoto row exists yet for this legacy record -
        # ordered_photos() must still surface the old field's photo.
        self.assertEqual(PersonalizationPhoto.objects.filter(personalization=legacy).count(), 0)
        self.assertEqual(len(legacy.ordered_photos()), 1)

        snapshot = legacy.to_snapshot()
        self.assertEqual(len(snapshot["photo_urls"]), 1)
        self.assertIsNotNone(snapshot["photo_url"])

        res = self.client.get(f"/api/personalization/cart-item/{cart_item_id}/", **self.guest_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["names"], "Old Customer")


class PersonalizationOrderSnapshotTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="photo-order-tester", password="testpass123")
        access = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        from orders.models import Address
        self.address = Address.objects.create(
            user=self.user, first_name="Test", last_name="User", phone="9999999999",
            address_line1="1 Test St", city="Hyderabad", state="Telangana", zip_code="500001",
        )
        self.category = Category.objects.create(name="Test Frames", slug="frames-order-personalization-test")
        self.product = Product.objects.create(
            category=self.category, name="Order Test Frame", slug="order-test-personalization-frame",
            price=Decimal("699.00"), description="Test.", stock=10,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, label="12x18 Inches", price=Decimal("1299.00"), order=0,
        )

    def test_order_snapshot_preserves_all_photos(self):
        self.client.post("/api/cart/add/", {"product": self.product.id, "variant": self.variant.id, "quantity": 1})
        items = self.client.get("/api/cart/items/").json()
        cart_item_id = items[0]["id"]

        self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"names": "Order Test", "photos": [make_image("a.jpg"), make_image("b.jpg"), make_image("c.jpg")]},
            format="multipart",
        )

        res = self.client.post("/api/orders/create/", {"address_id": self.address.id})
        self.assertEqual(res.status_code, 200)

        from orders.models import OrderItem
        order_item = OrderItem.objects.filter(product=self.product).latest("id")
        self.assertEqual(len(order_item.personalization_snapshot["photo_urls"]), 3)
        self.assertEqual(order_item.variant_snapshot["label"], "12x18 Inches")

    def test_historical_order_survives_photo_removal_from_live_cart(self):
        """Removing a photo from a NEW cart line must never be able to
        retroactively change a historical order's frozen snapshot -
        snapshots are copied at order-creation time, not referenced
        live."""
        self.client.post("/api/cart/add/", {"product": self.product.id, "variant": self.variant.id, "quantity": 1})
        cart_item_id = self.client.get("/api/cart/items/").json()[0]["id"]
        self.client.post(
            f"/api/personalization/cart-item/{cart_item_id}/",
            {"photos": [make_image("a.jpg"), make_image("b.jpg")]},
            format="multipart",
        )
        self.client.post("/api/orders/create/", {"address_id": self.address.id})

        from orders.models import OrderItem
        order_item = OrderItem.objects.filter(product=self.product).latest("id")
        self.assertEqual(len(order_item.personalization_snapshot["photo_urls"]), 2)

        # Cart is untouched by order creation (payment hasn't happened
        # yet) - removing a photo from the still-live cart line must not
        # affect the already-created order's snapshot.
        personalization = Personalization.objects.get(cart_item_id=cart_item_id)
        photo_to_remove = personalization.photos.first()
        self.client.delete(f"/api/personalization/cart-item/{cart_item_id}/photos/{photo_to_remove.id}/")

        order_item.refresh_from_db()
        self.assertEqual(len(order_item.personalization_snapshot["photo_urls"]), 2)


class GuestCartMergePersonalizationTests(TestCase):
    """Covers the real bug found while implementing this feature: the
    guest-to-user cart merge only matched on `product`, ignoring
    `variant` entirely - which would silently drop the customer's chosen
    size and orphan/duplicate personalisation photos on login."""

    def setUp(self):
        self.user = User.objects.create_user(username="merge-tester", password="testpass123")
        self.category = Category.objects.create(name="Test Frames", slug="frames-merge-test")
        self.product = Product.objects.create(
            category=self.category, name="Merge Test Frame", slug="merge-test-frame",
            price=Decimal("699.00"), description="Test.", stock=10,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, label="12x18 Inches", price=Decimal("1299.00"), order=0,
        )

    def test_merge_preserves_variant_and_photos_when_no_collision(self):
        guest_cart = Cart.objects.create(guest_id="merge-guest-1")
        item = CartItem.objects.create(cart=guest_cart, product=self.product, variant=self.variant, quantity=1)
        personalization = Personalization.objects.create(cart_item=item, names="Guest Customer")
        PersonalizationPhoto.objects.create(personalization=personalization, image=make_image("a.jpg"), display_order=0)
        PersonalizationPhoto.objects.create(personalization=personalization, image=make_image("b.jpg"), display_order=1)

        merge_guest_cart_to_user("merge-guest-1", self.user)

        user_cart = Cart.objects.get(user=self.user)
        merged_items = list(user_cart.items.all())
        self.assertEqual(len(merged_items), 1)
        self.assertEqual(merged_items[0].variant_id, self.variant.id)

        merged_personalization = Personalization.objects.get(cart_item=merged_items[0])
        self.assertEqual(merged_personalization.names, "Guest Customer")
        self.assertEqual(merged_personalization.photos.count(), 2)
        self.assertFalse(Cart.objects.filter(guest_id="merge-guest-1").exists())

    def test_merge_combines_quantity_on_real_collision_without_losing_personalization(self):
        user_cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=user_cart, product=self.product, variant=self.variant, quantity=1)

        guest_cart = Cart.objects.create(guest_id="merge-guest-2")
        guest_item = CartItem.objects.create(cart=guest_cart, product=self.product, variant=self.variant, quantity=2)
        personalization = Personalization.objects.create(cart_item=guest_item, names="Guest With Photos")
        PersonalizationPhoto.objects.create(personalization=personalization, image=make_image("a.jpg"), display_order=0)

        merge_guest_cart_to_user("merge-guest-2", self.user)

        merged_items = list(CartItem.objects.filter(cart=user_cart))
        self.assertEqual(len(merged_items), 1)
        self.assertEqual(merged_items[0].quantity, 3)

        merged_personalization = Personalization.objects.get(cart_item=merged_items[0])
        self.assertEqual(merged_personalization.names, "Guest With Photos")
        self.assertEqual(merged_personalization.photos.count(), 1)

    def test_merge_keeps_different_variants_of_same_product_separate(self):
        small = ProductVariant.objects.create(
            product=self.product, label="8x11 Inches", price=Decimal("799.00"), order=1,
        )
        user_cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=user_cart, product=self.product, variant=self.variant, quantity=1)

        guest_cart = Cart.objects.create(guest_id="merge-guest-3")
        CartItem.objects.create(cart=guest_cart, product=self.product, variant=small, quantity=1)

        merge_guest_cart_to_user("merge-guest-3", self.user)

        merged_items = list(CartItem.objects.filter(cart=user_cart))
        self.assertEqual(len(merged_items), 2)
        variant_ids = {i.variant_id for i in merged_items}
        self.assertEqual(variant_ids, {self.variant.id, small.id})


class PersonalizationMediaAndAdminTests(TestCase):
    """Covers the actual reported issue: uploaded photos not displaying
    in Django Admin. Verifies the full chain end to end - what gets
    stored in the DB, what URL it resolves to, that the URL is really
    served by Django, and that the Admin page renders a real <img> for
    every photo (not just the first, and not a broken link)."""

    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="media-admin-tester", password="testpass123", is_staff=True, is_superuser=True,
        )
        self.django_client = DjangoTestClient()
        self.django_client.force_login(self.staff)

        self.category = Category.objects.create(name="Test Frames", slug="frames-media-admin-test")
        self.product = Product.objects.create(
            category=self.category, name="Media Admin Test Frame", slug="media-admin-test-frame",
            price=Decimal("699.00"), description="Test.", stock=10,
        )
        cart = Cart.objects.create(guest_id="media-admin-guest")
        self.cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.personalization = Personalization.objects.create(cart_item=self.cart_item, names="Media Test")

    def test_uploaded_photo_stores_relative_path_not_absolute_url(self):
        """The DB must hold a storage-relative path like
        'personalizations/<id>/x.jpg' - never an absolute
        'http://localhost:8000/...' URL. Building the accessible URL is
        Django/the storage backend's job at read time via `.url`, not
        something the app should pre-bake into the stored value."""
        photo = PersonalizationPhoto.objects.create(
            personalization=self.personalization, image=make_image("a.jpg"), display_order=0,
        )
        self.assertTrue(photo.image.name.startswith("personalizations/"))
        self.assertNotIn("http://", photo.image.name)
        self.assertNotIn("localhost", photo.image.name)
        self.assertTrue(photo.image.url.startswith("/media/personalizations/"))

    # Note: this suite does not re-assert "the media URL is actually
    # servable over HTTP" via the Django test client, because Django's
    # test runner forces settings.DEBUG=False for every test run
    # (confirmed directly: printing settings.DEBUG inside a TestCase
    # prints False even though the real dev server's .env has
    # DEBUG=True) - and backend/urls.py only appends the dev-only
    # `static(MEDIA_URL, ...)` route when DEBUG is True. So under the
    # test runner there is never a route for /media/... regardless of
    # whether the feature works, making that specific check untestable
    # here through no fault of the app. It was instead verified directly
    # against the real running dev server: `curl -s -o /dev/null -w
    # "%{http_code} %{content_type}" http://localhost:8000/media/...`
    # returned "200 image/jpeg" for a real uploaded photo.

    def test_admin_change_page_renders_real_img_tag_for_uploaded_photo(self):
        photo = PersonalizationPhoto.objects.create(
            personalization=self.personalization, image=make_image("admin-preview.jpg"), display_order=0,
        )
        url = reverse("admin:personalization_personalization_change", args=[self.personalization.id])
        res = self.django_client.get(url)
        self.assertEqual(res.status_code, 200)
        content = res.content.decode()
        self.assertIn(f'<img src="{photo.image.url}"', content)

    def test_admin_change_page_renders_every_photo_not_just_the_first(self):
        photos = [
            PersonalizationPhoto.objects.create(
                personalization=self.personalization, image=make_image(f"p{i}.jpg"), display_order=i,
            )
            for i in range(4)
        ]
        url = reverse("admin:personalization_personalization_change", args=[self.personalization.id])
        content = self.django_client.get(url).content.decode()
        for photo in photos:
            self.assertIn(f'<img src="{photo.image.url}"', content)

    def test_admin_shows_legacy_single_photo_preview_for_backward_compatibility(self):
        legacy = Personalization.objects.create(cart_item=self.cart_item2(), photo=make_image("legacy-admin.jpg"))
        url = reverse("admin:personalization_personalization_change", args=[legacy.id])
        content = self.django_client.get(url).content.decode()
        self.assertIn(f'<img src="{legacy.photo.url}"', content)

    def test_admin_shows_no_image_placeholder_text_without_crashing_when_empty(self):
        url = reverse("admin:personalization_personalization_change", args=[self.personalization.id])
        res = self.django_client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("No image", res.content.decode())

    def cart_item2(self):
        cart = Cart.objects.create(guest_id="media-admin-guest-2")
        return CartItem.objects.create(cart=cart, product=self.product, quantity=1)
