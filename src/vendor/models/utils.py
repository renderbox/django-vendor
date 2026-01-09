import random
import string

from django.contrib.sites.models import Site
from django.utils.module_loading import import_string
from iso4217 import Currency

from vendor.config import AVAILABLE_CURRENCIES, VENDOR_DATA_ENCODER

encode = import_string("{}.encode".format(VENDOR_DATA_ENCODER))
decode = import_string("{}.decode".format(VENDOR_DATA_ENCODER))


###########
# UTILITIES
###########
def random_string(length=8, check=[]):
    letters = string.digits + string.ascii_uppercase
    value = "".join(random.sample(letters, length))

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
    available_currencies = set(AVAILABLE_CURRENCIES.keys()).intersection(
        msrp_currencies
    )

    if not currency and not available_currencies:
        return False

    if currency not in available_currencies:
        return False

    return True


def get_conversion_factor(currency_code):
    """Will look at the currency code and return the appropriate conversion factor to convert to cents.
    For example, USD has 2 decimal places, so the factor would be 100.
    JPY has 0 decimal places, so the factor would be 1.
    """
    try:
        currency = Currency(currency_code.upper())
        exp = getattr(currency, "exp", None)
        if exp is None:
            exp = getattr(currency, "exponent", None)
        if exp is None:
            exp = getattr(currency, "minor_unit", None)
        try:
            exp = int(exp)
        except (TypeError, ValueError):
            return 1
        return 10**exp if exp > 0 else 1
    except (KeyError, ValueError, AttributeError):
        return 1


def convert_to_minor_units(amount, currency_code):
    factor = get_conversion_factor(currency_code)
    return int(amount * factor)


def revert_to_major_units(amount, currency_code):
    factor = get_conversion_factor(currency_code)
    return amount / factor
