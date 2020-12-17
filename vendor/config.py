# App Settings
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

VENDOR_PRODUCT_MODEL = getattr(settings, "VENDOR_PRODUCT_MODEL", "vendor.Product")

VENDOR_PAYMENT_PROCESSOR = getattr(settings, "VENDOR_PAYMENT_PROCESSOR", "dummy.DummyProcessor")

DEFAULT_CURRENCY = getattr(settings, "DEFAULT_CURRENCY", "usd")

AVAILABLE_CURRENCIES = getattr(settings, "AVAILABLE_CURRENCIES", {'usd': _('USD Dollars')})

VENDOR_STATE = getattr(settings, "VENDOR_STATE", "DEBUG")

# Encryption settings
VENDOR_DATA_ENCODER = getattr(settings, "VENDOR_DATA_ENCODER", "vendor.encrypt.cleartext")
