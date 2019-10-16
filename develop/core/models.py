from django.utils.translation import ugettext as _
from django.db import models
from vendor.models import Offer


##########
# CATALOG
##########

# class Catalog(CreateUpdateModelBase):
#     '''
#     List of itmes being offered.
#     '''
#     name = models.CharField(_("Name"), max_length=100, blank=False)
#     slug = models.SlugField(_("Slug"))
#     site = models.ForeignKey(Site, related_name='catalog', on_delete=models.CASCADE, help_text="Which site is this inventory available to?")
#
#     def __str__(self):
#         return "{0} - {1}".format(self.site, self.name)


# Create your models here.
class Product(models.Model):
    name = models.CharField(_("Name"), max_length=50)

    def __str__(self):
        return self.name
