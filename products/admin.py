from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import (
    Category,
    SubCategory,
    Product,
    ProductImage,
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


# =====================================================
# PRODUCT
# =====================================================

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    inlines = [ProductImageInline]

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