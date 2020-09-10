from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product
from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile

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

    fixtures = []

    def setUp(self):
        pass

    def test_view_payment_status_code(self):
        # TODO: Implement Test
        pass
    
