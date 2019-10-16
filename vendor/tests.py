import unittest

from django.test import TestCase, Client, RequestFactory
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from vendor.models import Offer, Price, Invoice, OrderItem, Purchases
from core.models import Product


##################
# View Level Tests
##################

# class FactoryTests(TestCase):
#     factory = RequestFactory()
#
#     #TestCases for CART
#
#     def test_add_to_cart(self):
#         request = self.factory.post('/add-to-cart/1J0RO6LH/', data={})
#         self.assertEqual(request.method, "POST")
#
#
#     def test_retreive_cart(self):
#         request = self.factory.get('/retrieve-cart/1J0RO6LH/')
#         assert(request.content_type == "application/octet-stream")
#         assert(request.method == "GET")
#
#
#     def test_remove_item_from_cart(self):
#         request = self.factory.put('/remove-item-from-cart/1J0RO6LH/', data={})
#         self.assertEqual(request.method, "PUT")
#
#     def test_remove_single_item_from_cart(self):
#         request = self.factory.put('/remove-single-item-from-cart/1J0RO6LH/', data={})
#         self.assertEqual(request.method, "PUT")
#
#
#     def test_delete_cart(self):
#         request = self.factory.delete('/delete-cart/1J0RO6LH/')
#         assert(request.method == "DELETE")


###################
# CART CLIENT TEST
###################

class CartClientTest(TestCase):
    '''
    Tests for Cart Functionality
    '''

    def setUp(self):
        self.client = Client()
        product = Product.objects.create(name = "Test Product")
        offer = Offer.objects.create(product=product)

    def test_add_to_cart(self):
        '''
        Test for adding item to the cart
        '''

        pass


###################
# OFFER MODEL TEST
###################

class OfferModelTest(TestCase):
    '''
    Test for Offer Model Test
    '''

    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(name = "Test Product")


    def test_price_object_created(self):

        offer = Offer.objects.create(product=self.product)

        price_object_count = offer.sale_price.all().count()

        try:
            self.assertEqual(price_object_count, 1)

        except:     # Only print results if there is an error, but continue to raise the error for the testing tool
            print("")
            print(offer)
            raise


    def test_current_price(self):

        offer = Offer.objects.create(product=self.product, msrp = 80)

        price2 = Price.objects.create(offer = offer, cost = 90, priority=2, start_date = timezone.now(), end_date = timezone.now() + timezone.timedelta(days=1))

        try:
            self.assertEqual(offer.current_price(), offer.sale_price.all()[0].cost)

        except:     # Only print results if there is an error, but continue to raise the error for the testing tool
            print("")
            print(offer)
            print(offer.current_price())
            raise



###################
# PRICE MODEL TEST
###################

class PriceModelTest(TestCase):
    '''
    Test for Price Model Test
    '''

    def setUp(self):
        pass


#####################
# INVOICE MODEL TEST
#####################

class InvoiceModelTest(TestCase):
    '''
    Test for Invoice Model Test
    '''

    def setUp(self):
        pass


#######################
# ORDERITEM MODEL TEST
#######################

class OrderItemModelTest(TestCase):
    '''
    Test for OrderItem Model Test
    '''

    def setUp(self):
        pass


#######################
# PURCHASES MODEL TEST
#######################

class PurchasesModelTest(TestCase):
    '''
    Test for Purchases Model Test
    '''

    def setUp(self):
        pass
