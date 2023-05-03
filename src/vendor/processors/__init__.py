from django.utils.module_loading import import_string

from vendor.config import PaymentProcessorSiteConfig

def get_site_payment_processor(site):
    site_processor = PaymentProcessorSiteConfig(site)
    return import_string(f"vendor.processors.{site_processor.get_key_value('payment_processor')}")
