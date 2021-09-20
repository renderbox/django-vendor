# App Settings
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _

from siteconfigs.config import SiteConfigBaseClass
from siteconfigs.models import SiteConfigModel
from vendor.forms import PaymentProcessorForm, PaymentProcessorSiteSelectForm, SupportedProcessor


class PaymentProcessorSiteConfig(SiteConfigBaseClass):
    label = _("Promo Code Processor")
    default = {"processor": "base.PaymentProcessorBase"}
    form_class = PaymentProcessorForm
    key = ""
    instance = None

    def __init__(self, site=None):
        if site is None:
            site = Site.objects.get_current()
        self.key = ".".join([__name__, __class__.__name__])
        self.set_instance(site)
        super().__init__(site, self.key)

    # TODO: This should be implemented in the SiteConfigBaseClass  
    def save(self, valid_form):
        site_config, created = SiteConfigModel.objects.get_or_create(site=self.site, key=self.key)
        site_config.value = {"payment_processor": valid_form.cleaned_data['payment_processor']}
        site_config.site = self.site
        site_config.save()

    # TODO: This should be implemented in the SiteConfigBaseClass
    def set_instance(self, site):
        try:
            self.instance = SiteConfigModel.objects.get(site=site, key=self.key)
        except ObjectDoesNotExist:
            self.instance = None

    def get_form(self):
        return self.form_class(initial=self.get_initials())

    def get_initials(self):
        if self.instance:
            return {'payment_processor': [choice for choice in SupportedProcessor.choices if choice[0] == self.instance.value['payment_processor']][0]}
        return {'payment_processor': SupportedProcessor.choices[0]}

    def get_selected_processor(self):
        if self.instance:
            return [choice for choice in SupportedProcessor.choices if choice[0] == self.instance.value['payment_processor']][0]
        return SupportedProcessor.choices[0]  # Return Default Processors


class ProcessorSiteSelectSiteConfig(PaymentProcessorSiteConfig):
    label = _("Promo Code Processor")
    default = {"processor": "base.PromoProcessorBase"}
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
