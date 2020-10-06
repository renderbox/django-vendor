from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse


User = get_user_model()

class CheckoutViewTests(TestCase):

    fixtures = ['user', 'unit_test']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def test_view_checkout_account_success_code(self):
        response = self.client.get(reverse("vendor:checkout-account"))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Shipping Address')

    def test_view_checkout_payment_success_code(self):
        response = self.client.get(reverse("vendor:checkout-payment"))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Billing Address')

    def test_view_checkout_review_success_code(self):
        response = self.client.get(reverse("vendor:checkout-review"))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Review')

    def test_offers_list_status_code_fail_no_login(self):
        client = Client()
        response = client.get(reverse("vendor:checkout-review"))
        
        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)
    
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
    