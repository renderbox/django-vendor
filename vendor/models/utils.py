import random
import string

from django.contrib.sites.models import Site

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

