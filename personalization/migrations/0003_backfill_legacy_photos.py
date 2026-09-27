"""
Copies every existing Personalization.photo (the old single-photo field)
into a real PersonalizationPhoto row with display_order=0, so every
personalization - old or new - can be read uniformly through the new
`photos` relation. The legacy `photo` field itself is left untouched
(not cleared, not dropped) as a safety net; nothing after this point
writes to it any more, but historical data stays exactly as it was.

Idempotent: only creates a PersonalizationPhoto for a personalization
that doesn't already have one, so re-running this migration in a
development environment never duplicates photos.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    Personalization = apps.get_model("personalization", "Personalization")
    PersonalizationPhoto = apps.get_model("personalization", "PersonalizationPhoto")

    for p in Personalization.objects.exclude(photo="").exclude(photo__isnull=True):
        if PersonalizationPhoto.objects.filter(personalization=p).exists():
            continue
        PersonalizationPhoto.objects.create(
            personalization=p,
            image=p.photo.name,
            display_order=0,
        )


def unbackfill(apps, schema_editor):
    # Reversible in the sense Django requires, but deliberately a no-op:
    # the legacy `photo` field was never cleared, so there is nothing to
    # restore, and removing the backfilled rows isn't necessary for the
    # schema migration below this one to reverse cleanly.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personalization", "0002_personalizationphoto"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
