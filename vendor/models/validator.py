from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from iso4217 import Currency

from vendor.config import AVAILABLE_CURRENCIES
from vendor.models.utils import is_currency_available


# TODO: Validate multiple msrp lines
def validate_msrp_format(value):
    """
    This is a validator function used to validate an MSRP value added to the Product.
    """
    msrp = []
    if not value:
        return None

    msrp = value.split(',')

    if len(msrp) != 2 or not msrp:
        raise ValidationError(_("Invalid MSRP Value"), params={'value': value})
    
    if not msrp[0] or not msrp[1]:
        raise ValidationError(_("Invalid MSRP Value"), params={'value': value})

    if not msrp[0].lower() in Currency.__dict__:
        raise ValidationError(_("Invalid MSRP Value"), params={'value': value})


def validate_msrp(value):
    if value['msrp']['default'] not in AVAILABLE_CURRENCIES.keys():
        raise ValidationError(_(f'Currency not available'))
    
    if False in [ is_currency_available(value['msrp'].keys(), currency=msrp_currency) for msrp_currency in value['msrp'].keys() if msrp_currency != 'default']:
        raise ValidationError(_(f'Currency not available'))

