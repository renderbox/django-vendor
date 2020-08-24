from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product
from vendor.models import Offer, Price, Invoice, OrderItem, Reciept, CustomerProfile


class ModelInvoiceTests(TestCase):

    fixtures = ['site', 'user', 'product', 'price', 'offer', 'order_item', 'invoice']

    def setUp(self):
        self.existing_invoice = Invoice.objects.get(pk=1)
        
        self.new_invoice = Invoice(profile=CustomerProfile.objects.get(pk=1))
        self.new_invoice.save()

        self.shirt_offer = Offer.objects.get(pk=1)
        self.hamster = Offer.objects.get(pk=3)
        self.mug_offer = Offer.objects.get(pk=4)

    def test_add_offer(self):
        self.existing_invoice.add_offer(Offer.objects.get(pk=4))
        self.new_invoice.add_offer(self.mug_offer)

        self.assertIsNotNone(OrderItem.objects.get(invoice=self.new_invoice))
        self.assertEquals(OrderItem.objects.filter(invoice=self.existing_invoice).count(), 4)

    def test_fail_add_unavailable_offer(self):
        # TODO: Implement Tests
        pass

    def test_remove_offer(self):
        self.existing_invoice.remove_offer(Offer.objects.get(pk=3))

        self.assertEquals(OrderItem.objects.filter(invoice=self.existing_invoice).count(), 2)

    def test_update_totals(self):
        self.existing_invoice.update_totals()
        start_total = self.existing_invoice.total

        self.existing_invoice.add_offer(Offer.objects.get(pk=4))
        self.existing_invoice.update_totals()
        add_mug_total = self.existing_invoice.total

        self.existing_invoice.remove_offer(Offer.objects.get(pk=1))
        self.existing_invoice.update_totals()
        remove_shirt_total = self.existing_invoice.total

        self.assertEquals(start_total, 365.18)
        self.assertEquals(add_mug_total, 386.3)
        self.assertEquals(remove_shirt_total, 366.31)

    def test_add_quantity(self):
        start_quantity = self.existing_invoice.order_items.filter(offer=self.shirt_offer).first().quantity
        self.existing_invoice.add_offer(self.shirt_offer)
        end_quantity = self.existing_invoice.order_items.filter(offer=self.shirt_offer).first().quantity
        
        self.assertNotEquals(start_quantity, end_quantity)

    def test_remove_quantity(self):
        start_quantity = self.existing_invoice.order_items.filter(offer=self.shirt_offer).first().quantity
        self.existing_invoice.remove_offer(self.shirt_offer)
        end_quantity = self.existing_invoice.order_items.filter(offer=self.shirt_offer).first().quantity

        self.assertNotEquals(start_quantity, end_quantity)

    def test_remove_quantity_zero(self):
        start_quantity = self.existing_invoice.order_items.filter(offer=self.hamster).first().quantity
        self.existing_invoice.remove_offer(self.hamster)
        end_quantity = self.existing_invoice.order_items.filter(offer=self.hamster).count()

        self.assertNotEquals(start_quantity, end_quantity)

    


class ViewInvoiceTests(TestCase):
    
    def setUp(self):
        self.new_invoice = Invoice(profile=1)

    def test_view_cart(self):
        # TODO: Implement Tests
        pass
    
    def test_view_checkout(self):
        # TODO: Implement Tests
        pass
    
    def test_view_checkout_pay(self):
        '''
        In order to pay the total and shiping address should have been filled.
        '''
        # TODO: Implement Tests
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
    



