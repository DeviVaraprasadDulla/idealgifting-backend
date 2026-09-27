from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User


# ============================================
# CATEGORY
# ============================================

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    image = models.ImageField(
        upload_to="categories/",
        null=True,
        blank=True
    )

    is_trending = models.BooleanField(default=False)
    is_best_selling = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ============================================
# SUBCATEGORY
# ============================================

class SubCategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    is_best_selling = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} → {self.name}"


# ============================================
# PRODUCT
# ============================================

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.PositiveIntegerField(default=0)

    description = models.TextField()
    stock = models.IntegerField()
    order = models.PositiveIntegerField(default=0)

    # 🔥 IMPORTANT NEW FIELD
    is_best_selling = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)   # NEW
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        super().save(*args, **kwargs)

        if is_new and not self.slug:

            Product.objects.filter(
                pk=self.pk
            ).update(
                slug=f"{slugify(self.name)}-{self.id}"
            )

            self.slug = f"{slugify(self.name)}-{self.id}"

    def __str__(self):
        return self.name


# ============================================
# PRODUCT IMAGES
# ============================================

class ProductImage(models.Model):
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.name} image"


# ============================================
# PRODUCT VARIANTS (size / page-count pricing)
# ============================================
# A product with configurable options (a Frame's size, a Magazine's page
# count) gets one row per selectable option here, each with its own real
# price. Products without variants simply have none and keep using
# Product.price/discount_percentage exactly as before - this table is
# additive, not a replacement for the base price. The backend is always
# the source of truth for a variant's price; the frontend only renders
# what this table (via the API) says.

class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )
    label = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("product", "label")

    def __str__(self):
        return f"{self.product.name} - {self.label} (₹{self.price})"


# ============================================
# FILTERS
# ============================================

class Filter(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class FilterOption(models.Model):
    filter = models.ForeignKey(Filter, on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.filter.name} - {self.value}"

class ProductFilter(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    filter_option = models.ForeignKey(FilterOption, on_delete=models.CASCADE)


# ============================================
# REVIEW
# ============================================

class Review(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    rating = models.IntegerField()  # 1 to 5
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.product.name} - {self.rating}"

class CategoryFilter(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    filter = models.ForeignKey(Filter, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("category", "filter")

    def __str__(self):
        return f"{self.category.name} - {self.filter.name}"