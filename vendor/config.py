# App Settings
from django.conf import settings
from django import forms
from django.db.models import TextChoices
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from siteconfigs.config import SiteConfigBaseClass
from siteconfigs.models import SiteConfigModel

from vendor.utils import get_site_from_request


class SupportedPaymentProcessor(TextChoices):
    PROMO_CODE_BASE = ("base.PaymentProcessorBase", _("Default Processor"))
    AUTHORIZE_NET = ("authorizenet.AuthorizeNetProcessor", _("Authorize.Net"))
    STRIPE = ("stripe_processor.StripeProcessor", _("Stripe"))


class PaymentProcessorForm(forms.Form):
    payment_processor = forms.CharField(label=_("Payment Processor"), widget=forms.Select(choices=SupportedPaymentProcessor.choices))


class PaymentProcessorSiteSelectForm(PaymentProcessorForm):
    site = forms.CharField(label=_("Site"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['site'].widget = forms.Select(choices=[(site.pk, site.domain) for site in Site.objects.all()])


class PaymentProcessorSiteConfig(SiteConfigBaseClass):
    label = _("Promo Code Processor")
    default = {"payment_processor": "base.PaymentProcessorBase"}
    form_class = PaymentProcessorForm
    key = ""
    instance = None

    def __init__(self, site=None):
        
        if site is None:
            site = Site.objects.get_current()

        self.key = ".".join([__name__, __class__.__name__])
        super().__init__(site, self.key)
        
        if not self.instance:
            self.default['payment_processor'] = VENDOR_PAYMENT_PROCESSOR

    def get_form(self):
        return self.form_class(initial=self.get_initials())

    def get_initials(self):
        if self.instance:
            return {'payment_processor': [choice for choice in SupportedPaymentProcessor.choices if choice[0] == self.instance.value['payment_processor']][0]}

        return {'payment_processor': SupportedPaymentProcessor.choices[0]}

    def get_selected_processor(self):
        if self.instance:
            return [choice for choice in SupportedPaymentProcessor.choices if choice[0] == self.instance.value['payment_processor']][0]

        return SupportedPaymentProcessor.choices[0]  # Return Default Processors


class PaymentProcessorSiteSelectSiteConfig(PaymentProcessorSiteConfig):
    label = _("Promo Code Processor")
    default = {"payment_processor": "base.PromoProcessorBase"}
    form_class = PaymentProcessorSiteSelectForm
    key = ""
    instance = None

    def get_initials(self):
        initial = super().get_initials()
        initial['site'] = (self.site.pk, self.site.domain)
        
        return initial


VENDOR_PRODUCT_MODEL = getattr(settings, "VENDOR_PRODUCT_MODEL", "vendor.Product")

VENDOR_PAYMENT_PROCESSOR = getattr(settings, "VENDOR_PAYMENT_PROCESSOR", "dummy.DummyProcessor")

DEFAULT_CURRENCY = getattr(settings, "DEFAULT_CURRENCY", "usd")

AVAILABLE_CURRENCIES = getattr(settings, "AVAILABLE_CURRENCIES", {'usd': _('USD Dollars')})

VENDOR_STATE = getattr(settings, "VENDOR_STATE", "DEBUG")

# Encryption settings
VENDOR_DATA_ENCODER = getattr(settings, "VENDOR_DATA_ENCODER", "vendor.encrypt.cleartext")
