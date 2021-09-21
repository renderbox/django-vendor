from django.utils.module_loading import import_string
from django.core.exceptions import ObjectDoesNotExist

from vendor.config import PaymentProcessorSiteConfig
from vendor.processors.authorizenet import AuthorizeNetProcessor
from vendor.processors.base import PaymentProcessorBase
from vendor.processors.dummy import DummyProcessor
from siteconfigs.models import SiteConfigModel


def get_site_payment_processor(site):
    site_processor = PaymentProcessorSiteConfig()
    try:
        return import_string(f"vendor.processors.{SiteConfigModel.objects.get(site=site, key=site_processor.key).value['payment_processor']}")
    except ObjectDoesNotExist:
        # Should it return the default if not found?
        # raise ValueError("PromoProcessor has not been configured")
        return import_string(f"vendor.processors.{site_processor.default['payment_processor']}")
