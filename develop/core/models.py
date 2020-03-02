from django.utils.translation import ugettext as _
from django.db import models

from django.utils.text import slugify


##########
# PRODUCT
##########

class Product(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    slug = models.SlugField(_("Slug"), blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
