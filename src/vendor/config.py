# App Settings
from django.conf import settings
from django import forms
from django.db.models import TextChoices
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _

from siteconfigs.config import SiteConfigBaseClass


class SiteSelectForm(forms.Form):
    site = forms.ModelChoiceField(queryset=Site.objects.all())


class SupportedPaymentProcessor(TextChoices):
    PROMO_CODE_BASE = ("base.PaymentProcessorBase", _("Default Processor"))
    AUTHORIZE_NET = ("authorizenet.AuthorizeNetProcessor", _("Authorize.Net"))
    STRIPE = ("stripe_processor.StripeProcessor", _("Stripe"))


class PaymentProcessorForm(SiteSelectForm):
    payment_processor = forms.CharField(label=_("Payment Processor"), widget=forms.Select(choices=SupportedPaymentProcessor.choices))


class PaymentProcessorSiteConfig(SiteConfigBaseClass):
    label = _("Payment Processor")
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
        initial = super().get_initials()
        initial['site'] = (self.site.pk, self.site.domain)
        
        if self.instance:
            initial['payment_processor'] = [choice for choice in SupportedPaymentProcessor.choices if choice[0] == self.instance.value['payment_processor']][0]
        else:
            initial['payment_processor'] = SupportedPaymentProcessor.choices[0]
        
        return initial

    def get_selected_processor(self):
        if self.instance:
            return [choice for choice in SupportedPaymentProcessor.choices if choice[0] == self.instance.value['payment_processor']][0]

        return SupportedPaymentProcessor.choices[0]  # Return Default Processors


class StripeConnectAccountForm(SiteSelectForm):
    account_number = forms.CharField(max_length=120)


class StripeConnectAccountConfig(SiteConfigBaseClass):
    label = _("Stripe Connect Account")
    default = {'stripe_connect_account': None}
    form_class = StripeConnectAccountForm
    key = ''
    instance = None

    def __init__(self, site=None):
        
        if site is None:
            site = Site.objects.get_current()

        self.key = ".".join([__name__, __class__.__name__])
        super().__init__(site, self.key)
        

class VendorSiteCommissionForm(SiteSelectForm):
    commission = forms.IntegerField(min_value=0, max_value=100)


class VendorSiteCommissionConfig(SiteConfigBaseClass):
    label = _("Vendor Site Commission")
    default = {'commission': None}
    form_class = VendorSiteCommissionForm
    key = ''
    instance = None

    def __init__(self, site=None):
        
        if site is None:
            site = Site.objects.get_current()

        self.key = ".".join([__name__, __class__.__name__])
        super().__init__(site, self.key)


VENDOR_PRODUCT_MODEL = getattr(settings, "VENDOR_PRODUCT_MODEL", "vendor.Product")

VENDOR_PAYMENT_PROCESSOR = getattr(settings, "VENDOR_PAYMENT_PROCESSOR", "dummy.DummyProcessor")

DEFAULT_CURRENCY = getattr(settings, "DEFAULT_CURRENCY", "usd")

AVAILABLE_CURRENCIES = getattr(settings, "AVAILABLE_CURRENCIES", {'usd': _('USD Dollars')})

VENDOR_STATE = getattr(settings, "VENDOR_STATE", "DEBUG")

# Encryption settings
VENDOR_DATA_ENCODER = getattr(settings, "VENDOR_DATA_ENCODER", "vendor.encrypt.cleartext")


