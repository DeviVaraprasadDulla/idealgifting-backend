from django.urls import path
from .views import (
    CategoryListAPIView,
    SubCategoryListAPIView,
    ProductListAPIView,
    ProductDetailAPIView,
    ProductSearchAPIView,
    CategoryMegaMenuAPIView,
    CategoryDetailAPIView,
    SubmitReviewAPIView,
    FeaturedProductAPIView,
    CategoryFilterAPIView
)

urlpatterns = [

    # =========================
    # Categories
    # =========================
    path("categories/", CategoryListAPIView.as_view()),
    path("categories/<slug:slug>/", CategoryDetailAPIView.as_view()),

    # =========================
    # Subcategories
    # =========================
    path("subcategories/", SubCategoryListAPIView.as_view()),

    # =========================
    # Mega Menu
    # =========================
    path("mega-menu/", CategoryMegaMenuAPIView.as_view()),

    # =========================
    # Filters (Category-level)
    # =========================
    path("filters/", CategoryFilterAPIView.as_view()),

    # =========================
    # Products
    # =========================

    # 🔎 Search FIRST (important)
    path("products/search/", ProductSearchAPIView.as_view()),

    # ⭐ Featured
    path("products/featured/", FeaturedProductAPIView.as_view()),

    # 📦 Product List
    path("products/", ProductListAPIView.as_view()),

    # 📄 Product Detail LAST
    # Product Detail
        path(
            "products/<slug:slug>/",
            ProductDetailAPIView.as_view()
        ),

    # =========================
    # Submit Rating
    # =========================
    path("submit-review/", SubmitReviewAPIView.as_view()),
]