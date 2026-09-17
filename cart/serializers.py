from rest_framework import serializers
from .models import CartItem
from products.serializers import ProductFilterSerializer


class CartItemSerializer(serializers.ModelSerializer):
    # ✅ EXISTING FIELDS
    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    product_price = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()

    discount_percentage = serializers.IntegerField(
        source="product.discount_percentage",
        read_only=True
    )

    # Selected size/page-count option, if any - null for every product
    # without variants (unchanged behaviour).
    variant_id = serializers.IntegerField(source="variant.id", read_only=True, default=None)
    variant_label = serializers.CharField(source="variant.label", read_only=True, default=None)

    # 🔥 FIXED IMAGE FIELD
    product_image = serializers.SerializerMethodField()

    # ✅ EXTRA FIELDS
    product_id = serializers.IntegerField(
        source="product.id",
        read_only=True
    )

    product_slug = serializers.CharField(
        source="product.slug",
        read_only=True
    )

    product_category = serializers.IntegerField(
        source="product.category.id",
        read_only=True
    )

    # Real tagged Occasion/Feeling filters, reused by the frontend to
    # derive the same color-world tint the product card/PDP already use
    # for this product - never a fabricated or random assignment.
    product_filters = ProductFilterSerializer(
        source="product.productfilter_set",
        many=True,
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_id",
            "product_slug",
            "product_category",
            "variant_id",
            "variant_label",
            "quantity",
            "product_name",
            "product_price",
            "original_price",
            "discount_percentage",
            "product_image",
            "product_filters",
        ]

    # 🔥 GET FIRST PRODUCT IMAGE PROPERLY
    def get_product_image(self, obj):
        request = self.context.get("request")

        first_image = obj.product.images.first()

        if first_image and request:
            return request.build_absolute_uri(first_image.image.url)

        return None

    def _base_price(self, obj):
        """The selected variant's price when one is set, otherwise the
        product's own flat price - the same base the discount formula
        already applies to, unchanged."""
        return obj.variant.price if obj.variant_id else obj.product.price

    def get_original_price(self, obj):
        return float(self._base_price(obj))

    def get_product_price(self, obj):
        price = self._base_price(obj)
        discount = obj.product.discount_percentage

        if discount > 0:
            return round(
                float(price) - (float(price) * discount / 100),
                2
            )

        return float(price)
