import random
import string

from django.contrib.sites.models import Site
from django.utils.module_loading import import_string

from vendor.config import VENDOR_DATA_ENCODER, AVAILABLE_CURRENCIES

encode = import_string('{}.encode'.format(VENDOR_DATA_ENCODER))
decode = import_string('{}.decode'.format(VENDOR_DATA_ENCODER))

###########
# UTILITIES
###########

def random_string(length=8, check=[]):
    letters= string.digits + string.ascii_uppercase
    value = ''.join(random.sample(letters,length))

    if value not in check:
        return value
    return random_string(length=length, check=check)

def generate_sku():
    return random_string()

def set_default_site_id():
    return Site.objects.get_current()

def is_currency_available(msrp_currencies, currency=None):
    """
    Checks to see if the MSRP currencies for a product are available from the site's 
    configuration. If a currency is passed to the function, it will additionally check 
    if that currency is available from the filtered configured currencies and MSRP currencies.
    """
    available_currencies = set(AVAILABLE_CURRENCIES.keys()).intersection(msrp_currencies)

    if not currency and not available_currencies:
        return False
        
    if currency not in available_currencies:
        return False 
    
    return True
