from types import SimpleNamespace

from django.contrib.sites.models import Site
from django.test import TestCase

from vendor.processors.stripe import StripeProcessor, StripeQueryBuilder


class DummyStripeProcessor(StripeProcessor):
    """
    Minimal StripeProcessor that skips real credential setup and uses a stub stripe client.
    """

    def processor_setup(self, site, source=None):
        self.site = site
        self.source = source
        self.query_builder = StripeQueryBuilder()
        # stub stripe client; only attribute access is needed for these helper tests
        self.stripe = SimpleNamespace()


class StripeProcessorHelperTests(TestCase):
    fixtures = ["user", "unit_test"]

    def setUp(self):
        self.site = Site.objects.get(pk=1)
        self.processor = DummyStripeProcessor(self.site)

    def test_convert_decimal_to_integer_and_back(self):
        assert self.processor.convert_decimal_to_integer(0) == 0
        assert self.processor.convert_decimal_to_integer(10.55) == 1055
        assert self.processor.convert_integer_to_decimal(
            1055
        ) == self.processor.to_valid_decimal(10.55)

    def test_get_stripe_base_fee_amount_uses_defaults(self):
        # Defaults from STRIPE_BASE_COMMISSION = {"percentage": 2.9, "fixed": 0.3}
        fee = self.processor.get_stripe_base_fee_amount(100)
        self.assertAlmostEqual(fee, 3.2)

    def test_application_fee_defaults_to_zero(self):
        self.assertEqual(self.processor.get_application_fee_percent(), 0)
        self.assertEqual(self.processor.get_application_fee_amount(100), 0)

    def test_get_stripe_connect_account_default_none(self):
        self.assertIsNone(self.processor.get_stripe_connect_account())
