from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product
from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile



class ModelCustomerProfileTests(TestCase):
    
    fixtures = ['user', 'unit_test']

    def setUp(self):
        pass
    
    def test_get_invoice_cart(self):
        cp = CustomerProfile.objects.get(pk=1)
        invoice = cp.get_cart()

        self.assertIsNotNone(invoice)

    def test_new_invoice_cart(self):
        new_user = User()
        new_user.username = 'WMD'
        new_user.save()

        new_cp = CustomerProfile()
        new_cp.user = User.objects.get(pk=new_user.pk)
        new_cp.save()

        new_invoice = new_cp.get_cart()
        
        self.assertIsNotNone(new_invoice)
    
    def test_new_invoice_after_previous_paid(self):
        cp = CustomerProfile.objects.get(pk=1)
        invoice = cp.get_cart()

        invoice.status = Invoice.InvoiceStatus.COMPLETE
        invoice.save()

        new_invoice = cp.get_cart()
        new_invoice.save()

        self.assertNotEqual(invoice.pk, new_invoice.pk)
    

class ViewCustomerProfileTests(TestCase):
    def setUp(self):
        pass
