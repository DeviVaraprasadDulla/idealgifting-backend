from rest_framework import serializers
from django.db.models import Avg, Count
from decimal import Decimal

from .models import (
    Category,
    SubCategory,
    Product,
    ProductImage,
    Filter,
    FilterOption,
    ProductFilter,
    Review,
)

# =========================================================
# CATEGORY
# =========================================================

class CategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "order",
            "image",
            "is_trending",
            "is_best_selling",
            "is_active",
            "product_count",
        ]

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


# =========================================================
# SUBCATEGORY
# =========================================================

class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = SubCategory
        fields = [
            "id",
            "name",
            "slug",
            "order",
            "is_best_selling",
            "is_active",
            "category",
            "category_name",
        ]


# =========================================================
# PRODUCT IMAGES
# =========================================================

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "order"]


# =========================================================
# FILTERS
# =========================================================

class FilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filter
        fields = ["id", "name"]


class FilterOptionSerializer(serializers.ModelSerializer):
    filter_name = serializers.CharField(source="filter.name", read_only=True)

    class Meta:
        model = FilterOption
        fields = ["id", "filter", "filter_name", "value"]


# =========================================================
# PRODUCT FILTER (APPLIED OPTIONS)
# =========================================================

class ProductFilterSerializer(serializers.ModelSerializer):
    filter_option_value = serializers.CharField(
        source="filter_option.value",
        read_only=True
    )
    filter_name = serializers.CharField(
        source="filter_option.filter.name",
        read_only=True
    )

    class Meta:
        model = ProductFilter
        fields = [
            "id",
            "filter_option",
            "filter_name",
            "filter_option_value",
        ]


# =========================================================
# REVIEW SERIALIZER
# =========================================================

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user_name",
            "rating",
            "created_at",
        ]


# =========================================================
# PRODUCT (WITH RATING + REVIEWS)
# =========================================================

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    subcategory_name = serializers.CharField(
        source="subcategory.name",
        read_only=True
    )

    images = ProductImageSerializer(many=True, read_only=True)

    filters = ProductFilterSerializer(
        source="productfilter_set",
        many=True,
        read_only=True
    )

    discounted_price = serializers.SerializerMethodField()

    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "discount_percentage",
            "discounted_price",
            "description",
            "stock",
            "order",
            "is_best_selling",
            "is_featured",
            "is_active",
            "category",
            "subcategory",
            "category_name",
            "subcategory_name",
            "images",
            "filters",
            "average_rating",
            "rating_count",
            "reviews",
        ]

    def get_discounted_price(self, obj):
        if obj.discount_percentage > 0:
            discount = (obj.price * Decimal(obj.discount_percentage)) / Decimal(100)
            return obj.price - discount
        return obj.price

    def get_average_rating(self, obj):
        avg = obj.reviews.aggregate(avg=Avg("rating"))["avg"]
        return round(avg, 1) if avg else 0

    def get_rating_count(self, obj):
        return obj.reviews.count()


# =========================================================
# MEGA MENU SERIALIZERS
# =========================================================

class SubCategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ["id", "name", "slug"]


class CategoryWithSubSerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "image",
            "is_trending",
            "subcategories",
        ]

    def get_subcategories(self, obj):
        active_subcategories = obj.subcategories.filter(is_active=True)
        return SubCategoryMiniSerializer(
            active_subcategories,
            many=True
        ).data

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return