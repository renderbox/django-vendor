from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product
from vendor.models import Offer, Price, Invoice, OrderItem, Reciept


class ModelInvoiceTests(TestCase):

    def setUp(self):
        pass

    def test_add_offer(self):
        pass

    def test_fail_add_unavailable_offer(self):
        pass

    def test_remove_offer(self):
        pass

    def test_update_totals(self):
        pass


class ViewInvoiceTests(TestCase):
    
    def setUp(self):
        pass

    def test_view_cart(self):
        pass
    
    def test_view_checkout(self):
        pass
    
    def test_view_wait_screen(self):
        pass
    
    def test_view_failed_transaction(self):
        pass
    
    def test_view_purchase_complete(self):
        pass
    



