from django.utils.translation import ugettext as _
from django.db import models
from vendor.models import ProductModelBase

# Create your models here.
class Product(ProductModelBase):
    name = models.CharField(_("Name"), max_length=50)

