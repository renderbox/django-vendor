from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product

from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile



class ModelCustomerProfileTests(TestCase):
    
    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.user = User(username='test', first_name='Bob', last_name='Ross', password='helloworld')
        self.user.save()
        self.customer_profile = CustomerProfile()

        self.customer_profile_existing = CustomerProfile.objects.get(pk=1)

        self.customer_profile_user = CustomerProfile()
        self.customer_profile_user.user = User.objects.get(pk=1)
        self.customer_profile_user.save()

    def test_default_site_id_saved(self):
        self.customer_profile.user = User.objects.get(pk=1)
        self.customer_profile.save()

        self.assertEquals(Site.objects.get_current(), self.customer_profile.site)
    
    def test_get_invoice_cart(self):
        cp = CustomerProfile.objects.get(pk=1)
        invoice = cp.get_cart()

        self.assertIsNotNone(invoice)

    def test_new_invoice_cart(self):
        new_invoice = self.customer_profile_user.get_cart()
        
        self.assertIsNotNone(new_invoice)
    
    def test_new_invoice_after_previous_paid(self):
        cp = CustomerProfile.objects.get(pk=1)
        invoice = cp.get_cart()

        invoice.status = Invoice.InvoiceStatus.COMPLETE
        invoice.save()

        new_invoice = cp.get_cart()
        new_invoice.save()

        self.assertNotEqual(invoice.pk, new_invoice.pk)
    
    def test_get_cart_items_count_new_user(self):
        customer_profile = CustomerProfile(user=self.user)
        customer_profile.save()
        self.user.customer_profile.add(customer_profile)

        count = self.user.customer_profile.get(site=Site.objects.get_current()).get_cart_items_count()

        self.assertEquals(count, 0)

    def test_get_cart_items_count_no_items(self):
        customer_profile = CustomerProfile.objects.get(pk=1)

        count = customer_profile.get_cart_items_count()

        self.assertEquals(count, 3)

    def test_owns_product_true(self):
        product = Product.objects.get(pk=2)
        self.assertTrue(self.customer_profile_existing.has_product(product))

    def test_owns_product_false(self):
        product = Product.objects.get(pk=1)
        self.assertFalse(self.customer_profile_existing.has_product(product))

    def test_get_checkout_cart(self):
        cp = CustomerProfile.objects.get(pk=1)
        invoice = cp.get_cart()
        invoice.status = Invoice.InvoiceStatus.CHECKOUT
        invoice.save()

        self.assertIsNotNone(cp.get_checkout_cart())
        self.assertEqual(cp.get_checkout_cart().status, Invoice.InvoiceStatus.CHECKOUT)

    def test_gets_cart(self):
        cart = self.customer_profile_existing.get_cart_or_checkout_cart()
    
        self.assertEqual(cart.status, Invoice.InvoiceStatus.CART)

    def test_gets_checkout_cart(self):
        invoice = Invoice.objects.get(pk=1)
        self.customer_profile_existing.invoices.add(Invoice.objects.create(status=Invoice.InvoiceStatus.CHECKOUT))

        cart = self.customer_profile_existing.get_cart_or_checkout_cart()
    
        self.assertEqual(cart.status, Invoice.InvoiceStatus.CHECKOUT)


class ViewCustomerProfileTests(TestCase):
    def setUp(self):
        pass
