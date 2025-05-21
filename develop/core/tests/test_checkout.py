from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class CheckoutViewTests(TestCase):

    fixtures = ["user", "unit_test"]

    def setUp(self):
        pass

    def test_fail_view_checkout_pay_no_address(self):
        # TODO: Implement Tests
        pass

    def test_fail_view_checkout_pay_no_card_info(self):
        # TODO: Implement Tests
        pass

    def test_fail_view_checkout_error_tax(self):
        # TODO: Implement Tests
        pass

    def test_fail_view_checkout_pay_process_failed(self):
        # TODO: Implement Tests
        pass

    def test_success_view_checkout_payment_processed(self):
        # TODO: Implement Tests
        pass

    def test_view_wait_screen(self):
        # TODO: Implement Tests
        pass

    def test_view_failed_transaction(self):
        # TODO: Implement Tests
        pass

    def test_view_purchase_complete(self):
        # TODO: Implement Tests
        pass
