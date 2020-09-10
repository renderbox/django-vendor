# App Settings
from django.conf import settings

VENDOR_PRODUCT_MODEL = getattr(settings, "VENDOR_PRODUCT_MODEL", "vendor.Product")