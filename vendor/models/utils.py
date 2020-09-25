import random
import string

from django.contrib.sites.models import Site
from django.utils.module_loading import import_string

from vendor.config import VENDOR_DATA_ENCODER

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
