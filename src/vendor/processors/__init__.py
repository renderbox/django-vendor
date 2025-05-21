from django.core.exceptions import ObjectDoesNotExist
from django.utils.module_loading import import_string
from siteconfigs.models import SiteConfigModel

from vendor.config import PaymentProcessorSiteConfig
from vendor.processors.authorizenet import AuthorizeNetProcessor
from vendor.processors.base import PaymentProcessorBase
from vendor.processors.dummy import DummyProcessor
from vendor.processors.stripe import (
    PRORATION_BEHAVIOUR_CHOICE,
    StripeProcessor,
    StripeQueryBuilder,
)


def get_site_payment_processor(site):
    site_processor = PaymentProcessorSiteConfig(site)
    return import_string(
        f"vendor.processors.{site_processor.get_key_value('payment_processor')}"
    )
