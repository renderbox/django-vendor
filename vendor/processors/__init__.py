from django.utils.module_loading import import_string
from django.core.exceptions import ObjectDoesNotExist
from vendor.config import PaymentProcessorSiteConfig
from siteconfigs.models import SiteConfigModel


def get_site_payment_processor(site):
    site_processor = PaymentProcessorSiteConfig()
    try:
        return import_string(f"vendor.processors.{SiteConfigModel.objects.get(site=site, key=site_processor.key).value}")
    except ObjectDoesNotExist:
        default_config = PaymentProcessorSiteConfig()
        # Should it return the default if not found?
        # raise ValueError("PromoProcessor has not been configured")
        return import_string(f"vendor.processors.{default_config.default[default_config.key]}")
