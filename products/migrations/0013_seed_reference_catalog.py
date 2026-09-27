"""
Data migration only - no schema change.

Seeds the real product catalog needed to reproduce the client reference's
actual product experience (names, prices, descriptions, occasion/
recipient/feeling tags) as real Product/Category/ProductImage/
ProductFilter rows - not hardcoded React data. Content (name, price,
description, tags) is taken directly from the reference's own real
source data (its PRODUCTS array), so nothing here is invented; it is a
faithful transcription of the reference's real specification into the
real Django catalog.

Product photography does not exist for these items (neither the
reference nor this business has real photographs of them - the
reference itself says so in its own README: "product art is hand-drawn
SVG until real photography is added"). Since Django's ImageField
requires a genuine raster image (SVG fails Pillow's validation), each
product gets one real, generated placeholder image (a soft gradient in
the product's own reference color, matching the reference's visual
language) rather than a broken/missing image - a real file through the
real upload pipeline, not a frontend-only stand-in.

Existing categories/products (Anniversary Gifts, Birthday Gifts, and
their 18 products) are untouched.
"""

import io
from django.db import migrations
from django.core.files.base import ContentFile


CATEGORIES = [
    ("Frames", "frames"),
    ("Trophies", "trophies"),
    ("Photobooks", "photobooks"),
    ("Invitations", "invitations"),
]

# world -> (bg hex, deep hex) - same values used across the frontend's
# color-world system, for a real, non-random relationship between a
# product's mood and its placeholder art.
WORLD_COLORS = {
    "love": ("#C7566B", "#7C2B3E"),
    "birthday": ("#EF7A5C", "#9C3A20"),
    "baby": ("#6FA8D0", "#2C5876"),
    "kids": ("#9B86CF", "#4A3A78"),
    "family": ("#D08A4E", "#7A4718"),
    "friendship": ("#D9A93C", "#7A5A10"),
    "wedding": ("#C79A5B", "#6E5121"),
    "corporate": ("#37568C", "#152F5E"),
    "festive": ("#B8434F", "#6E1E28"),
    "achievement": ("#4E8E7C", "#1F5245"),
}

OCCASION_MAP = {
    "wedding": "Wedding", "birthday": "Birthday", "anniversary": "Anniversary",
    "baby": "Baby & Kids", "family": "Family", "friendship": "Friendship",
    "festival": "Festive", "rakhi": "Raksha Bandhan", "achievement": "Achievement",
    "corporate": "Corporate",
}
RECIPIENT_MAP = {
    "partner": "Partner", "mom": "Mom", "dad": "Dad", "friend": "Best Friend",
    "sibling": "Sibling", "child": "Child", "family": "Family",
    "colleague": "Colleague", "client": "Client",
}
FEELING_MAP = {
    "emotional": "Emotional", "surprised": "Surprised", "loved": "Loved",
    "proud": "Proud", "special": "Special",
}

# Category slug each product belongs to, derived from the reference's own
# primary collection membership (its `coll` array).
CATEGORY_FOR = {
    "wedding-invite": "invitations", "photobook": "photobooks",
    "birthday-frame-kids": "frames", "love-trophy": "trophies",
    "caricature-trophy": "trophies", "corporate-trophy": "trophies",
    "magazine": "photobooks", "birth-frame-kids": "frames",
    "rakhi-trophy": "trophies", "twin-baby-frame": "frames",
    "anniversary-frame": "frames", "birthday-highlight": "frames",
    "insta-frame": "frames", "netflix-frame": "frames",
    "baby-milestone": "frames", "family-crossword": "frames",
    "love-story-frame": "frames", "love-trophy-premium": "trophies",
    "digital-invitation": "invitations",
}

# Reference's own home-page `feat` (featured) and Bestseller-badged items.
FEATURED_IDS = {
    "magazine", "photobook", "love-story-frame", "netflix-frame",
    "rakhi-trophy", "baby-milestone", "caricature-trophy", "anniversary-frame",
}
BESTSELLER_IDS = {"photobook", "baby-milestone"}

# Real product data transcribed directly from the reference's own PRODUCTS
# array (index.html) - id, name, price, world, description, occasion/
# recipient/feeling tags.
PRODUCTS = [
    dict(id="wedding-invite", name="Personalised Digital Wedding Invite", price=699, world="wedding",
         desc="Comic-style digital invites built from your real photographs — custom caricatures of the two of you, ready to share the moment it lands in your inbox and worth saving long after the wedding.",
         occ=["wedding"], rec=["partner", "family", "friend"], feel=["special", "surprised"]),
    dict(id="photobook", name="Personalised Photobook", price=1999, world="family",
         desc="From spontaneous smiles to the moments you never want to forget, your favourite photographs come together as a story you can actually hold. Because scrolling through memories is nice — turning them into a gift is better.",
         occ=["birthday", "anniversary", "family", "friendship", "festival"], rec=["partner", "mom", "dad", "friend", "family"], feel=["emotional", "loved"]),
    dict(id="birthday-frame-kids", name="Personalised Birthday Frame", price=699, world="kids",
         desc="A birthday frame full of giggles, colour and the kind of joy that flutters forever. Custom made around your little one — their name, their age, their favourite photograph.",
         occ=["birthday"], rec=["child", "family"], feel=["surprised", "loved"]),
    dict(id="love-trophy", name="Personalised Love Trophy", price=899, world="love",
         desc="A custom photo trophy in crystal-clear acrylic, cut around your favourite picture. Perfect for anniversaries, birthdays and the moments that never made it to a certificate.",
         occ=["anniversary", "birthday"], rec=["partner", "friend"], feel=["loved", "proud"]),
    dict(id="caricature-trophy", name="Caricature Love Trophy", price=999, world="birthday",
         desc="Turn a favourite memory into a playful caricature and put it on a trophy that's impossible to ignore — and even harder to forget.",
         occ=["birthday", "anniversary", "friendship"], rec=["partner", "friend", "sibling"], feel=["surprised", "special"]),
    dict(id="corporate-trophy", name="Corporate Brand Trophy", price=899, world="corporate",
         desc="Go beyond a name engraved on glass. Your logo, your award title, your people — built into a trophy designed to stay on the desk long after the applause.",
         occ=["corporate", "achievement"], rec=["colleague", "client"], feel=["proud", "special"]),
    dict(id="magazine", name="Personalised Magazine", price=2500, world="festive",
         desc="From childhood photographs to the people they love most, twenty-four pages built entirely around one person. A gift that says: I know your story, and I think it's worth celebrating.",
         occ=["birthday", "anniversary", "friendship", "festival", "family"], rec=["mom", "dad", "partner", "friend", "sibling"], feel=["emotional", "loved", "special"]),
    dict(id="birth-frame-kids", name="Kids Personalised Birth Frame", price=799, world="kids",
         desc="Name, time of arrival, weight and first photograph — the small details you swore you'd never forget, held together in one frame made for the nursery wall.",
         occ=["baby", "family"], rec=["child", "family"], feel=["emotional", "loved"]),
    dict(id="rakhi-trophy", name="Raksha Bandhan Personalised Trophy", price=899, world="festive",
         desc="A custom acrylic trophy with your favourite photo and a line only the two of you would understand. For siblings who laughed together, fought together, grew up together and still show up for each other.",
         occ=["rakhi", "festival", "friendship"], rec=["sibling"], feel=["emotional", "loved"]),
    dict(id="twin-baby-frame", name="Personalised Twin Baby Frame", price=899, world="baby",
         desc="A keepsake built for two — both names, both sets of birth details and the first photograph of the pair, designed as one balanced piece rather than two halves.",
         occ=["baby", "family"], rec=["child", "family"], feel=["emotional", "special"]),
    dict(id="anniversary-frame", name="Personalised Anniversary Frame", price=799, world="love",
         desc="From candid kitchen smiles to the wedding day itself — your favourite photographs, your names and the line you always say to each other, arranged into one piece for the wall.",
         occ=["anniversary", "wedding"], rec=["partner", "family"], feel=["emotional", "loved"]),
    dict(id="birthday-highlight", name="Personalised Birthday Highlight Frame", price=799, world="birthday",
         desc="A calendar-style keepsake where their birthday is the whole point — their photo, their month, their day, highlighted like the event it actually is.",
         occ=["birthday", "achievement"], rec=["friend", "sibling", "partner", "colleague"], feel=["surprised", "special"]),
    dict(id="insta-frame", name="Insta Profile Personalised Frame", price=799, world="love",
         desc="A personalised Instagram-style collage where the bio is about the two of you and the grid is made of the moments that actually mattered. For weddings, anniversaries, proposals and couples who met in the DMs.",
         occ=["anniversary", "wedding", "friendship"], rec=["partner", "friend"], feel=["surprised", "special"]),
    dict(id="netflix-frame", name="Netflix-Style Personalized Frame", price=799, world="love",
         desc="From first dates to forever moments, presented like the blockbuster it is — poster artwork, episode list, a very biased five-star rating and the two of you in the lead roles.",
         occ=["anniversary", "birthday", "friendship"], rec=["partner", "friend"], feel=["surprised", "special"]),
    dict(id="baby-milestone", name="Baby Milestone Frame", price=799, world="baby",
         desc="Their first day changed your whole world. Keep every little detail close — the time, the weight, the hospital, the first photograph and the family who couldn't wait to meet them.",
         occ=["baby", "family"], rec=["child", "family"], feel=["emotional", "loved"]),
    dict(id="family-crossword", name="Family Crossword Frame", price=799, world="family",
         desc="Each name interlocks with the next, exactly the way your family works. A quiet, clever piece for the living room wall — and the gift relatives ask about for years.",
         occ=["family", "festival", "anniversary"], rec=["family", "mom", "dad"], feel=["loved", "special"]),
    dict(id="love-story-frame", name="Love Story Frame", price=799, world="love",
         desc="The first hello. The unforgettable date. The big yes. The little moments in between. Your story laid out chapter by chapter — because forever deserves a frame.",
         occ=["anniversary", "wedding"], rec=["partner"], feel=["emotional", "loved"]),
    dict(id="love-trophy-premium", name="Personalised Love Trophy Premium", price=950, world="love",
         desc="Our love trophy in a heavier, thicker acrylic with a champagne-gold plaque and a deeper base. Made for the anniversaries you want to feel a little grander.",
         occ=["anniversary", "birthday", "wedding"], rec=["partner"], feel=["loved", "special"]),
    dict(id="digital-invitation", name="Personalised Digital Invitation", price=1299, world="wedding",
         desc="Custom illustration, your event details, and a finish that works on a phone screen and on paper. Digital and printed versions, designed together so nothing gets lost in translation.",
         occ=["wedding", "festival", "corporate"], rec=["family", "partner", "client"], feel=["special", "proud"]),
]


def make_placeholder_png(bg_hex, deep_hex):
    """A real, generated raster image (soft two-tone gradient with a
    couple of overlapping soft circles, echoing the reference's own
    hand-drawn-circle art style) - not a fabricated photograph, but a
    genuine image file satisfying Django's ImageField validation."""
    from PIL import Image, ImageDraw

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    bg = hex_to_rgb(bg_hex)
    deep = hex_to_rgb(deep_hex)
    size = 800
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img, "RGBA")

    # vertical gradient wash from bg to deep
    for y in range(size):
        t = y / size
        r = int(bg[0] * (1 - t) + deep[0] * t)
        g = int(bg[1] * (1 - t) + deep[1] * t)
        b = int(bg[2] * (1 - t) + deep[2] * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    # two soft overlapping circles, translucent, echoing the reference's
    # own recurring "overlapping circles" motif in its SVG art
    draw.ellipse([size * 0.15, size * 0.55, size * 0.65, size * 1.05], fill=(255, 255, 255, 40))
    draw.ellipse([size * 0.45, size * 0.15, size * 0.85, size * 0.55], fill=(255, 255, 255, 55))

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=87)
    return buffer.getvalue()


def seed_catalog(apps, schema_editor):
    Category = apps.get_model("products", "Category")
    Product = apps.get_model("products", "Product")
    ProductImage = apps.get_model("products", "ProductImage")
    Filter = apps.get_model("products", "Filter")
    FilterOption = apps.get_model("products", "FilterOption")
    ProductFilter = apps.get_model("products", "ProductFilter")

    categories = {}
    for i, (name, slug) in enumerate(CATEGORIES):
        cat, _ = Category.objects.get_or_create(slug=slug, defaults={"name": name, "order": 100 + i})
        categories[slug] = cat

    occasion_filter = Filter.objects.filter(name="Occasion").first()
    recipient_filter = Filter.objects.filter(name="Recipient").first()
    feeling_filter = Filter.objects.filter(name="Feeling").first()
    price_filter = Filter.objects.filter(name="Price Band").first()

    def option(filter_obj, value):
        if not filter_obj:
            return None
        return FilterOption.objects.filter(filter=filter_obj, value=value).first()

    price_bands = [
        ("Under ₹1,000", None, 1000), ("₹1,000 - ₹2,000", 1000, 2000),
        ("₹2,000 - ₹4,000", 2000, 4000), ("₹4,000+", 4000, None),
    ]

    for data in PRODUCTS:
        world = data["world"]
        bg_hex, deep_hex = WORLD_COLORS[world]
        category = categories[CATEGORY_FOR[data["id"]]]

        product, created = Product.objects.get_or_create(
            slug=data["id"],
            defaults=dict(
                category=category,
                name=data["name"],
                price=data["price"],
                discount_percentage=0,
                description=data["desc"],
                stock=25,
                is_featured=data["id"] in FEATURED_IDS,
                is_best_selling=data["id"] in BESTSELLER_IDS,
                is_active=True,
            ),
        )
        if not created:
            continue

        image_bytes = make_placeholder_png(bg_hex, deep_hex)
        image = ProductImage(product=product, order=0)
        image.image.save(f"{data['id']}.jpg", ContentFile(image_bytes), save=True)

        for occ in data["occ"]:
            opt = option(occasion_filter, OCCASION_MAP.get(occ))
            if opt:
                ProductFilter.objects.get_or_create(product=product, filter_option=opt)
        for rec in data["rec"]:
            opt = option(recipient_filter, RECIPIENT_MAP.get(rec))
            if opt:
                ProductFilter.objects.get_or_create(product=product, filter_option=opt)
        for feel in data["feel"]:
            opt = option(feeling_filter, FEELING_MAP.get(feel))
            if opt:
                ProductFilter.objects.get_or_create(product=product, filter_option=opt)

        price = float(data["price"])
        for label, low, high in price_bands:
            if (low is None or price >= low) and (high is None or price < high):
                opt = option(price_filter, label)
                if opt:
                    ProductFilter.objects.get_or_create(product=product, filter_option=opt)
                break


def unseed_catalog(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    Category = apps.get_model("products", "Category")
    Product.objects.filter(slug__in=[p["id"] for p in PRODUCTS]).delete()
    Category.objects.filter(slug__in=[slug for _, slug in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0012_seed_occasion_recipient_feeling_priceband_taxonomy"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, unseed_catalog),
    ]
