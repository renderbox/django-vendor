from random import randrange
from unittest import skipIf

# import stripe
from django.conf import settings
from django.test import Client, TestCase
from siteconfigs.models import SiteConfigModel

@skipIf(
    (getattr(settings, 'STRIPE_PUBLIC_KEY', None) or getattr(settings, 'STRIPE_SECRET_KEY', None)) is None,
    "Stripe environment variables not set, skipping tests",
)
class StripeProcessorTests(TestCase):
    fixtures = ["user", "unit_test"]

    VALID_CARD_NUMBERS = [
        "4242424242424242",  # visa
        "4000056655665556",  # visa debit
        "5555555555554444",  # mastercard
        "5200828282828210",  # mastercard debit
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.contrib.auth import get_user_model
        global User
        User = get_user_model()

    def setup_processor_site_config(self):
        
        self.processor_site_config = SiteConfigModel()
        self.processor_site_config.site = self.existing_invoice.site
        self.processor_site_config.key = "vendor.config.PaymentProcessorSiteConfig"
        self.processor_site_config.value = {
            "payment_processor": "stripe.StripeProcessor"
        }
        self.processor_site_config.save()

    def setup_user_client(self):
        from vendor.models import CustomerProfile
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.customer = CustomerProfile.objects.get(pk=1)
        self.client.force_login(self.user)
