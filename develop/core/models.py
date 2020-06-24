from django.utils.translation import ugettext as _
from django.db import models

from vendor.models import ProductBase

##########
# CATALOG
##########

class Catalog(models.Model):
    '''
    An Example Catalog use for Development
    '''
    name = models.CharField(_("Name"), max_length=80, blank=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=settings.SITE_ID)

    def __str__(self):
        return self.name

##########
# PRODUCT
##########

class Product(ProductBase):
    '''
    An Example Product use for Development
    '''
    name = models.CharField(_("Name"), max_length=80, blank=True)
    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name="products")

