from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product
from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile


class ReceiptModelTests(TestCase):

    fixtures = []

    def setUp(self):
        pass

    def test_receipt_save_subscription(self):
        # TODO: Implement Test
        pass

    def test_receipt_save_perpertual(self):
        # TODO: Implement Test
        pass

    def test_receipt_save_one_time_use(self):
        # TODO: Implement Test
        pass
    

class ReceiptViewTests(TestCase):

    fixtures = []

    def setUp(self):
        pass

    def test_view_receipt_status_code(self):
        # TODO: Implement Test
        pass
    