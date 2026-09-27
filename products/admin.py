from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import (
    Category,
    SubCategory,
    Product,
    ProductImage,
    ProductVariant,
    Filter,
    FilterOption,
    ProductFilter,
)

# =====================================================
# CATEGORY
# =====================================================

@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "name",
        "order",
        "is_best_selling",
        "is_active",
    )
    list_editable = ("order", "is_best_selling", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order",)
    search_fields = ("name",)


# =====================================================
# SUBCATEGORY
# =====================================================

@admin.register(SubCategory)
class SubCategoryAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "order",
        "is_best_selling",
        "is_active",
    )
    list_editable = ("order", "is_best_selling", "is_active")
    list_filter = ("category", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order",)
    search_fields = ("name",)


# =====================================================
# PRODUCT IMAGE INLINE
# =====================================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("label", "price", "order", "is_active")


# =====================================================
# PRODUCT
# =====================================================

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    inlines = [ProductImageInline, ProductVariantInline]

    list_display = (
        "id",
        "name",
        "category",
        "subcategory",
        "price",
        "discount_percentage",
        "order",
        "is_best_selling",
        "is_featured",
        "is_active",
    )

    list_editable = (
        "order",
        "is_best_selling",
        "is_featured",
        "is_active",
    )

    list_filter = (
        "category",
        "subcategory",
        "is_active",
        "is_best_selling",
        "is_featured",
    )

    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order",)
    search_fields = ("name", "description")


# =====================================================
# PRODUCT VARIANTS
# =====================================================

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "label", "price", "order", "is_active")
    list_editable = ("price", "order", "is_active")
    list_filter = ("is_active", "product__category")
    search_fields = ("label", "product__name")
    ordering = ("product", "order")


# =====================================================
# FILTER
# =====================================================

@admin.register(Filter)
class FilterAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(FilterOption)
class FilterOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "filter", "value")
    list_filter = ("filter",)
    search_fields = ("value",)


# =====================================================
# PRODUCT FILTER
# =====================================================

@admin.register(ProductFilter)
class ProductFilterAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "filter_option")
    list_filter = ("product", "filter_option")