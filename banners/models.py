from django.db import models

# Create your models here.
from django.db import models

from django.db import models

class Banner(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to="banners/")
    order = models.PositiveIntegerField(default=0)  # display order
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]  # frontend display order

    def __str__(self):
        return self.title
