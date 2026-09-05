"""
Data migration only - no schema change.

Seeds the existing generic Filter/FilterOption/ProductFilter system with
real taxonomy content (Occasion, Recipient, Feeling, Price Band) so the
reference's occasion/recipient/gift-finder browsing can run against real
data instead of a hardcoded catalog.

Tagging rules are intentionally mechanical and auditable - never a guess:

- Occasion: derived directly from each product's real, already-assigned
  Category ("Birthday Gifts" -> Birthday, "Anniversary Gifts" -> Anniversary).
- Recipient: "Partner" for every Anniversary-category product (an anniversary
  is inherently between partners); "Child" only for the one product whose
  real name explicitly says "First Birthday".
- Feeling: applied only when the product's own real name contains an
  explicit matching word (love/sweetheart/romance/heart -> Loved,
  surprise -> Surprised, "first birthday" -> Special). No feeling is
  assigned where no such word appears in the product's real name.
- Price Band: computed purely from each product's real numeric price.

All ten reference Occasions and all nine reference Recipients are created
as real FilterOption rows so the taxonomy architecture is complete and
ready for future catalog growth, but ProductFilter associations - the
links that make a page show real products - are only created for the
combinations above. Every other occasion/recipient option honestly shows
zero products today rather than being backfilled with invented tags.
"""

from django.db import migrations


OCCASIONS = [
    "Birthday", "Anniversary", "Wedding", "Baby & Kids", "Family",
    "Friendship", "Raksha Bandhan", "Achievement", "Festive", "Corporate",
]

RECIPIENTS = [
    "Partner", "Mom", "Dad", "Best Friend", "Sibling",
    "Child", "Family", "Colleague", "Client",
]

FEELINGS = ["Emotional", "Surprised", "Loved", "Proud", "Special"]

# category name (real, already on Product.category) -> Occasion option value
CATEGORY_TO_OCCASION = {
    "Birthday Gifts": "Birthday",
    "Anniversary Gifts": "Anniversary",
}

# category name -> Recipient option value (anniversary is inherently partner-directed)
CATEGORY_TO_RECIPIENT = {
    "Anniversary Gifts": "Partner",
}

# product slug -> Recipient option value, only where the product's own real
# name gives an explicit, unambiguous signal
SLUG_TO_RECIPIENT = {
    "golden-star-first-birthday-cake": "Child",
}

# keyword (checked case-insensitively against the product's real name) -> Feeling
FEELING_KEYWORDS = {
    "love": "Loved",
    "sweetheart": "Loved",
    "romance": "Loved",
    "heart": "Loved",
    "surprise": "Surprised",
    "first birthday": "Special",
}

PRICE_BANDS = [
    ("Under ₹1,000", None, 1000),
    ("₹1,000 - ₹2,000", 1000, 2000),
    ("₹2,000 - ₹4,000", 2000, 4000),
    ("₹4,000+", 4000, None),
]


def seed_taxonomy(apps, schema_editor):
    Filter = apps.get_model("products", "Filter")
    FilterOption = apps.get_model("products", "FilterOption")
    ProductFilter = apps.get_model("products", "ProductFilter")
    Product = apps.get_model("products", "Product")

    occasion_filter, _ = Filter.objects.get_or_create(name="Occasion")
    recipient_filter, _ = Filter.objects.get_or_create(name="Recipient")
    feeling_filter, _ = Filter.objects.get_or_create(name="Feeling")
    price_filter, _ = Filter.objects.get_or_create(name="Price Band")

    occasion_options = {
        v: FilterOption.objects.get_or_create(filter=occasion_filter, value=v)[0]
        for v in OCCASIONS
    }
    recipient_options = {
        v: FilterOption.objects.get_or_create(filter=recipient_filter, value=v)[0]
        for v in RECIPIENTS
    }
    feeling_options = {
        v: FilterOption.objects.get_or_create(filter=feeling_filter, value=v)[0]
        for v in FEELINGS
    }
    price_options = {
        label: FilterOption.objects.get_or_create(filter=price_filter, value=label)[0]
        for label, _, _ in PRICE_BANDS
    }

    def tag(product, option):
        ProductFilter.objects.get_or_create(product=product, filter_option=option)

    for product in Product.objects.select_related("category").all():
        category_name = product.category.name if product.category else None

        occasion_value = CATEGORY_TO_OCCASION.get(category_name)
        if occasion_value:
            tag(product, occasion_options[occasion_value])

        recipient_value = SLUG_TO_RECIPIENT.get(product.slug) or CATEGORY_TO_RECIPIENT.get(category_name)
        if recipient_value:
            tag(product, recipient_options[recipient_value])

        name_lower = product.name.lower()
        for keyword, feeling_value in FEELING_KEYWORDS.items():
            if keyword in name_lower:
                tag(product, feeling_options[feeling_value])

        price = float(product.price)
        for label, low, high in PRICE_BANDS:
            if (low is None or price >= low) and (high is None or price < high):
                tag(product, price_options[label])
                break


def unseed_taxonomy(apps, schema_editor):
    Filter = apps.get_model("products", "Filter")
    Filter.objects.filter(name__in=["Occasion", "Recipient", "Feeling", "Price Band"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0011_delete_subcategoryfilter"),
    ]

    operations = [
        migrations.RunPython(seed_taxonomy, unseed_taxonomy),
    ]
