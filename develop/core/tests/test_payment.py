from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product
from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile

User = get_user_model()

class PaymentModelTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        pass

    def test_payment_save_completed(self):
          
        pass

    def test_pyament_save_refund(self):
        # TODO: Implement Test
        pass
    
    def test_payment_save_failed(self):
        # TODO: Implement Test
        pass
    

class PaymentViewTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def test_view_payment_status_code(self):
        response = self.client.get(reverse("vendor:purchase-summary", kwargs={'pk': 1}))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Purchase Confirmation')

    def test_offers_list_status_code_fail_no_login(self):
        client = Client()
        response = client.get(reverse("vendor:purchase-summary", kwargs={'pk': 1}))
        
        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)
    
