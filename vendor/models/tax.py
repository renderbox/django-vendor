# import copy
# import random
# import string
# import uuid
# # import pycountry

# from django.conf import settings
# from django.contrib.sites.models import Site
# from django.core.exceptions import ValidationError
from django.db import models
# from django.db.models.signals import post_save
# from django.urls import reverse
# from django.utils import timezone
# from django.utils.text import slugify
from django.utils.translation import ugettext as _

# from address.models import AddressField
# from autoslug import AutoSlugField
# from iso4217 import Currency

#####################
# TAX CLASSIFIER
#####################

class TaxClassifier(models.Model):
    '''
    This for things like "Digital Goods", "Furniture" or "Food" which may or
    may not be taxable depending on the location.  These are determined by the
    manager of all sites.  
    
    These classifiers will retain certian provider specific codes that are used
    to help calculate the tax liability in the sale.
    '''
    name = models.CharField(_("Name"), max_length=80, blank=True)
    taxable = models.BooleanField()
    # info = models.ManyToManyField("vendor.TaxInfo")                 # Which taxes is this subject to and where.  This is for a more complex tax setup

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Product Classifier")
        verbose_name_plural = _("Product Classifiers")


#########
# TAXES
#########

# class TaxInfo(models.Model):
#     '''
#     This is meant to start with a simple sales tax estimation.
#     It will likely tie to someting from a 3rd party service, like Avalara eventually.
#     It will still indicate the type of product it is for tax purposes.
#     By default, they should only be set-up in the location where the business is run from.
#     '''
#     name = models.CharField(_("Name"), max_length=80, blank=True)
#     rate = models.FloatField()
#     currency = models.IntegerField(_("Currency"), choices=CurrencyChoices.choices)  # ISO 4217 Standard codes
#     start_date = models.DateTimeField(_("Start Date"), help_text="When should this tax rate start?")
#     description = models.TextField(_("Description"))
#     region_type = models.IntegerField(choices=REGION_TYPE_CHOICES)  # Where does this tax apply
#     region_name = models.CharField()
