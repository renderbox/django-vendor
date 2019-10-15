from django.utils.translation import ugettext as _
from django.db import models
from vendor.models import Offer

# Create your models here.
class Product(models.Model):
    name = models.CharField(_("Name"), max_length=50)

    def __str__(self):
        return self.name
