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
    original_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    discount_percentage = serializers.IntegerField(
        source="product.discount_percentage",
        read_only=True
    )

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
    def get_product_price(self, obj):
        price = obj.product.price
        discount = obj.product.discount_percentage

        if discount > 0:
            return round(
                float(price) - (float(price) * discount / 100),
                2
            )

        return float(price)
