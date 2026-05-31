from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from .models import (
    Category,
    SubCategory,
    Product,
    FilterOption,
    Review,
    CategoryFilter,
)

from .serializers import (
    CategorySerializer,
    SubCategorySerializer,
    ProductSerializer,
    CategoryWithSubSerializer,
)


# =====================================================
# CATEGORY LIST
# =====================================================

class CategoryListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        queryset = Category.objects.filter(is_active=True)

        if self.request.query_params.get("is_trending") == "true":
            queryset = queryset.filter(is_trending=True)

        return queryset.annotate(
            product_count=Count("product")
        ).order_by("order")


# =====================================================
# CATEGORY DETAIL
# =====================================================

class CategoryDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        category = get_object_or_404(
            Category,
            slug=slug,
            is_active=True
        )

        return Response({
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "image": category.image.url if category.image else None,
            "is_trending": category.is_trending,
            "is_best_selling": category.is_best_selling,
        })


# =====================================================
# SUBCATEGORY LIST
# =====================================================

class SubCategoryListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SubCategorySerializer

    def get_queryset(self):
        queryset = SubCategory.objects.filter(is_active=True)
        category_id = self.request.query_params.get("category")

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset


# =====================================================
# MEGA MENU
# =====================================================

class CategoryMegaMenuAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategoryWithSubSerializer

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("order")

    def get_serializer_context(self):
        return {"request": self.request}


# =====================================================
# CATEGORY FILTERS (NEW CLEAN VERSION)
# =====================================================

class CategoryFilterAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category_id = request.query_params.get("category")

        if not category_id:
            return Response([])

        products = Product.objects.filter(
            category_id=category_id,
            is_active=True
        )

        filter_options = FilterOption.objects.filter(
            productfilter__product__in=products
        ).select_related("filter").distinct()

        filter_map = {}

        for option in filter_options:
            filter_id = option.filter.id

            if filter_id not in filter_map:
                filter_map[filter_id] = {
                    "filter_id": option.filter.id,
                    "filter_name": option.filter.name,
                    "options": []
                }

            filter_map[filter_id]["options"].append({
                "id": option.id,
                "value": option.value
            })

        return Response(list(filter_map.values()))

        for cf in category_filters:
            options = FilterOption.objects.filter(filter=cf.filter)

            response_data.append({
                "filter_id": cf.filter.id,
                "filter_name": cf.filter.name,
                "options": [
                    {"id": opt.id, "value": opt.value}
                    for opt in options
                ]
            })

        return Response(response_data)


# =====================================================
# PRODUCT LIST (FILTER + SEARCH + SORT)
# =====================================================

class ProductListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = (
            Product.objects
            .filter(is_active=True)
            .select_related("category", "subcategory")
            .prefetch_related("images", "productfilter_set", "reviews")
        )

        category_slug = self.request.query_params.get("category_slug")
        subcategory_slug = self.request.query_params.get("subcategory_slug")
        filter_ids = self.request.query_params.get("filters")
        sort = self.request.query_params.get("sort")
        search = self.request.query_params.get("search")

        # 🔍 SEARCH
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(category__name__icontains=search) |
                Q(subcategory__name__icontains=search)
            )

        # 📂 CATEGORY FILTER
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        if subcategory_slug:
            queryset = queryset.filter(subcategory__slug=subcategory_slug)

        # 🎯 FILTER OPTIONS
        if filter_ids:
            filter_ids = filter_ids.split(",")
            queryset = queryset.filter(
                productfilter__filter_option_id__in=filter_ids
            ).distinct()

        # 🔃 SORTING
        if sort == "price_low":
            queryset = queryset.order_by("price")
        elif sort == "price_high":
            queryset = queryset.order_by("-price")
        elif sort == "best_selling":
            queryset = queryset.order_by("-is_best_selling", "order")
        else:
            queryset = queryset.order_by("order")

        return queryset


# =====================================================
# FEATURED PRODUCTS
# =====================================================

class FeaturedProductAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return (
            Product.objects
            .filter(is_active=True, is_featured=True)
            .select_related("category", "subcategory")
            .prefetch_related("images")
            .order_by("order")[:8]
        )


# =====================================================
# PRODUCT DETAIL
# =====================================================

class ProductDetailAPIView(RetrieveAPIView):
    permission_classes = [AllowAny]

    serializer_class = ProductSerializer

    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects
            .filter(is_active=True)
            .select_related("category", "subcategory")
            .prefetch_related(
                "images",
                "productfilter_set"
            )
        )

# =====================================================
# PRODUCT SEARCH (NAVBAR AUTOCOMPLETE)
# =====================================================

class ProductSearchAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.GET.get("q", "").strip()

        if not q:
            return Response([])

        products = (
            Product.objects
            .filter(is_active=True)
            .filter(
                Q(name__icontains=q) |
                Q(category__name__icontains=q) |
                Q(subcategory__name__icontains=q)
            )
            .prefetch_related("images")[:8]
        )

        results = []

        for p in products:
            image_url = None
            first_image = p.images.first()

            if first_image:
                image_url = request.build_absolute_uri(first_image.image.url)

            results.append({
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "image": image_url
            })

        return Response(results)


# =====================================================
# SUBMIT REVIEW
# =====================================================

class SubmitReviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product")
        rating = request.data.get("rating")

        if not product_id or not rating:
            return Response(
                {"error": "Product and rating required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if int(rating) < 1 or int(rating) > 5:
            return Response(
                {"error": "Rating must be between 1 and 5"},
                status=status.HTTP_400_BAD_REQUEST
            )

        Review.objects.update_or_create(
            product_id=product_id,
            user=request.user,
            defaults={"rating": rating}
        )

        return Response({"message": "Rating submitted successfully"})