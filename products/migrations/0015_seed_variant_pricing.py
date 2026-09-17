"""
Seeds real ProductVariant rows (size/page-count pricing) for every real
Frame, Trophy, Magazine and Photobook product, using the exact prices
supplied by the business:

Frames:      8x11 Inches -> Rs.799   | 12x18 Inches -> Rs.1,299
Trophies:    6x8 Inches  -> Rs.999   | 8x10 Inches  -> Rs.1,499
Magazines:   12 Pages -> Rs.999 | 16 Pages -> Rs.1,499 | 20 Pages -> Rs.1,999
Photobooks:  12 Pages -> Rs.999 | 16 Pages -> Rs.1,499 | 20 Pages -> Rs.1,999

Every product in the real Frames/Trophies categories gets the same size
variant set; the real Magazine and Photobook products get the page-count
set. Idempotent via get_or_create keyed on (product, label), matching
the model's unique_together constraint, so re-running this migration in
a development environment never creates duplicates.
"""
from decimal import Decimal
from django.db import migrations

FRAME_VARIANTS = [
    ("8x11 Inches", Decimal("799.00"), 0),
    ("12x18 Inches", Decimal("1299.00"), 1),
]

TROPHY_VARIANTS = [
    ("6x8 Inches", Decimal("999.00"), 0),
    ("8x10 Inches", Decimal("1499.00"), 1),
]

PAGE_COUNT_VARIANTS = [
    ("12 Pages", Decimal("999.00"), 0),
    ("16 Pages", Decimal("1499.00"), 1),
    ("20 Pages", Decimal("1999.00"), 2),
]


def seed_variants(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    ProductVariant = apps.get_model("products", "ProductVariant")

    def apply_variants(queryset, variants):
        for product in queryset:
            for label, price, order in variants:
                ProductVariant.objects.get_or_create(
                    product=product,
                    label=label,
                    defaults={"price": price, "order": order, "is_active": True},
                )

    apply_variants(
        Product.objects.filter(category__slug="frames", is_active=True),
        FRAME_VARIANTS,
    )
    apply_variants(
        Product.objects.filter(category__slug="trophies", is_active=True),
        TROPHY_VARIANTS,
    )
    apply_variants(
        Product.objects.filter(category__slug="photobooks", slug="magazine", is_active=True),
        PAGE_COUNT_VARIANTS,
    )
    apply_variants(
        Product.objects.filter(category__slug="photobooks", slug="photobook", is_active=True),
        PAGE_COUNT_VARIANTS,
    )


def unseed_variants(apps, schema_editor):
    ProductVariant = apps.get_model("products", "ProductVariant")
    labels = {label for label, _, _ in FRAME_VARIANTS + TROPHY_VARIANTS + PAGE_COUNT_VARIANTS}
    ProductVariant.objects.filter(label__in=labels).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0014_productvariant"),
    ]

    operations = [
        migrations.RunPython(seed_variants, unseed_variants),
    ]
