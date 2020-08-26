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

from address.models import AddressField
# from autoslug import AutoSlugField
# from iso4217 import Currency

from .profile import CustomerProfile


#####################
# ADDRESS
#####################

class Address(models.Model):
    """Address model for use in purchasing.

    Example:
        Potential Format to use.

        Frau                [title]
        Mag. Maria Muster   [recipient]
        Gartenweg 8         [address1]
                            [address2]
        Rafing              [locality]
        3741 PULKAU         [postal code]
        AUSTRIA             [country]

    Args:
        name (int): The name of the address to use
        profile (CustomerProfile): Foreign Key connection to the Customer Profile
        address (Address): Special Address fields

    Returns:
        Address(): Returns an instance of the Address model
    """
    name = models.CharField(_("Name"), max_length=80, blank=True)                                           # If there is only a Product and this is blank, the product's name will be used, oterhwise it will default to "Bundle: <product>, <product>""
    profile = models.ForeignKey(CustomerProfile, verbose_name=_("Customer Profile"), null=True, on_delete=models.CASCADE, related_name="addresses")
    address = AddressField()
