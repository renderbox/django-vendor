from django.core.exceptions import ObjectDoesNotExist  # noqa: F401
from django.utils.module_loading import import_string
from siteconfigs.models import SiteConfigModel  # noqa: F401

from vendor.config import PaymentProcessorSiteConfig
from vendor.processors.authorizenet import AuthorizeNetProcessor  # noqa: F401
from vendor.processors.base import PaymentProcessorBase  # noqa: F401
from vendor.processors.dummy import DummyProcessor  # noqa: F401
from vendor.processors.stripe import (  # noqa: F401
    PRORATION_BEHAVIOUR_CHOICE,
    StripeProcessor,
    StripeQueryBuilder,
)


def get_site_payment_processor(site):
    site_processor = PaymentProcessorSiteConfig(site)
    return import_string(
        f"vendor.processors.{site_processor.get_key_value('payment_processor')}"
    )
