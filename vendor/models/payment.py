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

##########
# PAYMENT
##########

class Payment(models.Model):
    '''
    Payments
    - Payments are typically from a Credit Card, PayPal or ACH
    - Multiple Payments can be applied to an invoice
    - Gift cards can be used as payments
    - Discounts are Payment credits
    '''
    invoice = models.ForeignKey("vendor.Invoice", verbose_name=_("Invoice"), on_delete=models.CASCADE, related_name="payments")
    created = models.DateTimeField("date created", auto_now_add=True)
    transaction = models.CharField(_("Transaction ID"), max_length=50)
    provider = models.CharField(_("Payment Provider"), max_length=16)
    amount = models.FloatField(_("Amount"))
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), blank=True, null=True, on_delete=models.SET_NULL, related_name="payments")
    billing_address = models.ForeignKey("vendor.Address", verbose_name=_("payments"), on_delete=models.CASCADE, blank=True, null=True)
    result = models.TextField(_("Result"), blank=True, null=True)
    success = models.BooleanField(_("Successful"), default=False)


# class Coupon(models.Model):
#     pass


# class GiftCode(models.Model):
#     pass
