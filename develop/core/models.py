from django.utils.translation import ugettext as _
from django.db import models
from vendor.models import Offer
from autoslug import AutoSlugField

##########
# PRODUCT
##########

class Product(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    slug = AutoSlugField(_("Slug"), populate_from='name')

    def __str__(self):
        return self.name
