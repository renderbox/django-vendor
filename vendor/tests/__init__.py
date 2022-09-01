
from .test_processor import *
from .test_stripe import *






# TODO: Check which tests are still worth keepting
# import os
# import json
# import unittest

# from django.test import TestCase, Client, RequestFactory
# from django.urls import reverse
# from django.utils import timezone
# from django.contrib.auth.models import User

# from vendor.models import Offer, Price, Invoice, OrderItem, Refund
# from vendor.models import Product


# ########################
# # API VIEW CLIENT TESTS
# ########################

# ####################
# # CART CLIENT TESTS
# ####################

# ##############
# # ADD TO CART
# ##############

# class AddToCartClientTest(TestCase):
#     '''
#     Tests for AddToCart Functionality
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)

#     def test_add_to_cart_create_invoice(self):
#         '''
#         Test for adding item to the cart when there is no invoice for the user with cart status.
#         '''
#         self.client.force_login(self.user)

#         offer = Offer.objects.create(product = self.product)
#         invoice = Invoice.objects.filter(user = self.user, status = 0).count()

#         data = {
#             "offer": offer.sku
#         }

#         uri = reverse('vendor-add-to-cart-api')
#         response = self.client.post(uri, data)

#         new_invoice = Invoice.objects.filter(user = self.user, status = 0).count()
#         orderitem = OrderItem.objects.filter(offer = offer).count()

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Created Response Code
#             self.assertEqual(invoice, 0)
#             self.assertEqual(new_invoice, 1)
#             self.assertEqual(orderitem, 1)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


#     def test_add_to_cart_create_order_item(self):
#         '''
#         Test for adding item to the cart
#         '''
#         self.client.force_login(self.user)
#         offer = Offer.objects.create(product = self.product)

#         # offer = Offer.objects.create(product = self.product)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.filter(offer = offer, invoice = invoice).count()

#         data = {
#             "offer": offer.sku
#         }

#         uri = reverse('vendor-add-to-cart-api')
#         response = self.client.post(uri, data)

#         new_orderitem = OrderItem.objects.filter(offer = offer, invoice = invoice).count()

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Created Response Code
#             self.assertEqual(orderitem, 0)
#             self.assertEqual(new_orderitem, 1)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


#     def test_add_to_cart_increment_offer_quantity(self):
#         '''
#         Test for adding item to the cart which is already in the cart
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user=self.user, ordered_date=timezone.now())
#         orderitem = OrderItem.objects.create(invoice=invoice, offer=offer)

#         data = {
#             "offer": offer.sku
#         }

#         uri = reverse('vendor-add-to-cart-api')             # Add the offer to the current user's cart
#         response = self.client.post(uri, data)

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Created Response Code
#             self.assertEqual(orderitem.quantity, 1)
#             self.assertGreater(OrderItem.objects.get(offer=offer, invoice=invoice).quantity, 1)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise

# ###################
# # DELETE FROM CART
# ###################

# class RemoveItemFromCartClientTest(TestCase):
#     '''
#     Tests for Cart Functionality
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)

#     def test_remove_item_from_cart(self):
#         '''
#         Test for removing the item from the cart
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)

#         uri = reverse('vendor-remove-from-cart-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         order = OrderItem.objects.filter(offer = offer, invoice = invoice).count()

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Created Response Code
#             self.assertEqual(order, 0)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


#     def test_remove_item_from_cart_fail_1(self):
#         '''
#         Test for removing the item not present in the cart
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())

#         uri = reverse('vendor-remove-from-cart-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         try:
#             self.assertEqual(response.status_code, 404)     # 404 -> Created Response Code

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


#     def test_remove_item_from_cart_fail_2(self):
#         '''
#         Test for removing the item from the cart with no active cart for the user
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)

#         uri = reverse('vendor-remove-from-cart-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         try:
#             self.assertEqual(response.status_code, 400)     # 404 -> Created Response Code

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


# ##################################
# # DECREASE ITEM QUANTITY IN CART
# ##################################

# class DecreaseItemQuantityClientTest(TestCase):
#     '''
#     Tests for Cart Functionality
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)

#     def test_decrease_quantity_from_cart(self):
#         '''
#         Test for decreasing the quantity of the item already in the cart
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)
        
#         data = {
#             "offer": offer.sku
#         }

#         increase_item_quantity_uri = reverse('vendor-add-to-cart-api')
#         cart_response = self.client.post(increase_item_quantity_uri, data)

#         quantity = OrderItem.objects.get(offer = offer, invoice = invoice).quantity

#         uri = reverse('vendor-remove-single-item-from-cart-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Created Response Code
#             self.assertEqual(quantity, 2)
#             self.assertLess(OrderItem.objects.get(offer = offer, invoice = invoice).quantity, quantity)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


#     def test_decrease_quantity_from_cart_fail_1(self):
#         '''
#         Test for decreasing the quantity of the item when there is no active cart for the user
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)

#         uri = reverse('vendor-remove-single-item-from-cart-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         try:
#             self.assertEqual(response.status_code, 400)     # 400 -> Created Response Code

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


#     def test_decrease_quantity_from_cart_fail_2(self):
#         '''
#         Test for decreasing the quantity of the item not present in the cart
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())

#         uri = reverse('vendor-remove-single-item-from-cart-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         try:
#             self.assertEqual(response.status_code, 404)     # 404 -> Created Response Code

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


# ##################################
# # INCREASE ITEM QUANTITY IN CART
# ##################################

# class IncreaseItemQuantityTest(TestCase):
#     '''
#     Tests for Cart Functionality
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)

#     def test_increase_item_quantity(self):
#         '''
#         Test for increasing the quantity of an item in the cart
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)

#         quantity = OrderItem.objects.get(offer = offer, invoice = invoice).quantity

#         uri = reverse('vendor-increase-item-quantity-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         updated_quantity = OrderItem.objects.get(offer = offer, invoice = invoice).quantity

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Created Response Code
#             self.assertGreater(updated_quantity, quantity)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise

#     def test_increase_item_quantity_fail_1(self):
#         '''
#         Test for increasing the quantity of the item when there is no active cart for the user
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)

#         uri = reverse('vendor-increase-item-quantity-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         try:
#             self.assertEqual(response.status_code, 400)     # 400 -> Created Response Code

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


#     def test_increase_item_quantity_fail_2(self):
#         '''
#         Test for increasing the quantity of the item not present in the cart
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())

#         uri = reverse('vendor-increase-item-quantity-api', kwargs={'sku': offer.sku})
#         response = self.client.patch(uri)

#         try:
#             self.assertEqual(response.status_code, 404)     # 404 -> Created Response Code

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


# #################
# # RETRIEVE CART
# #################

# class RetrieveCartClientTest(TestCase):
#     '''
#     Tests for Cart Functionality
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)
#         self.product2 = Product.objects.get(pk=3)

#     def test_cart_retrieve(self):
#         '''
#         Test for retrieving a cart for the user
#         '''

#         self.client.force_login(self.user)

#         offer = Offer.objects.get(pk=2)     # todo: use fixtures
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)
#         offer2 = Offer.objects.create(product = self.product2, name = self.product2.name, msrp = 90.0)
#         orderitem2 = OrderItem.objects.create(invoice = invoice, offer = offer2, quantity = 2)

#         check_data = {
#               "username": "testuser",
#               "order_items": [
#                 {
#                   "sku": "MWSHDGQN",
#                   "name": "Test Product",
#                   "price": "50.00",
#                   "quantity": 1
#                 },
#                 {
#                   "sku": "MWSHDGQN",
#                   "name": "Test Product2",
#                   "price": "90.00",
#                   "quantity": 1
#                 }
#               ],
#               "item_count": 2
#             }

#         uri = reverse('vendor-user-cart-retrieve-api')
#         response = self.client.get(uri)

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Return Response Code
#             self.assertEqual(response.data.keys(), check_data.keys())
#             self.assertEqual(response.data["order_items"][0].keys(), check_data["order_items"][0].keys())
#             self.assertEqual(response.data["item_count"], invoice.order_items.all().count())

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response)
#             print(response.data)
#             raise


#     def test_cart_retrieve_fail(self):
#         '''
#         Test for retrieving a cart when there is no active cart for the user
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)

#         uri = reverse('vendor-user-cart-retrieve-api')
#         response = self.client.get(uri)

#         try:
#             self.assertEqual(response.status_code, 404)     # 404 -> Return Response Code

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response)
#             raise


# #########################
# # RETRIEVE ORDER SUMMARY
# #########################

# class RetrieveOrderSummaryClientTest(TestCase):
#     '''
#     Tests for retrieving order summary
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)
#         self.product2 = Product.objects.get(pk=3)

#     def test_order_summary_retrieve(self):
#         '''
#         Test for retrieving order summary for the user
#         '''

#         self.client.force_login(self.user)

#         offer = Offer.objects.get(pk=2)
#         price = offer.sale_price.filter(start_date__lte= timezone.now(), end_date__gte=timezone.now()).order_by('priority').first()

#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())

#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)

#         offer2 = Offer.objects.create(product = self.product2, name = self.product2.name, msrp = 90.0)
#         price2 = offer2.sale_price.filter(start_date__lte= timezone.now(), end_date__gte=timezone.now()).order_by('priority').first()

#         orderitem2 = OrderItem.objects.create(invoice = invoice, offer = offer2, quantity = 2)

#         check_data = {
#               "username": "testuser",
#               "order_items": [
#                 {
#                   "sku": "MWSHDGQN",
#                   "name": "Test Product",
#                   "price": "50.00",
#                   "item_total": "50.00",
#                   "quantity": 1
#                 },
#                 {
#                   "sku": "MWSHDGQN",
#                   "name": "Test Product2",
#                   "price": "90.00",
#                   "item_total": "180.00",
#                   "quantity": 1
#                 }
#               ],
#               "total": "230.00"
#             }

#         uri = reverse('vendor-order-summary-retrieve-api')
#         response = self.client.get(uri)

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Return Response Code
#             self.assertEqual(response.data.keys(), check_data.keys())
#             self.assertEqual(response.data["order_items"][0].keys(), check_data["order_items"][0].keys())

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response)
#             print(response.data)
#             raise


#     def test_order_summary_retrieve_fail(self):
#         '''
#         Test for retrieving order summary for the user when there is no active cart
#         '''

#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)

#         uri = reverse('vendor-order-summary-retrieve-api')
#         response = self.client.get(uri)

#         try:
#             self.assertEqual(response.status_code, 404)     # 404 -> Return Response Code

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response)
#             raise


# ##############
# # DELETE CART
# ##############

# class DeleteCartClientTest(TestCase):
#     '''
#     Test for deleting a cart
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)
#         self.product2 = Product.objects.get(pk=3)

#     def test_user_cart_delete(self):
#         '''
#         Test for deleting a cart contents.
#         '''

#         self.client.force_login(self.user)
        
#         uri = reverse('vendor-user-cart-delete-api')
#         response = self.client.delete(uri)

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Return Response Code
#             self.assertEqual(Invoice.objects.all().filter(status=0).count(), 2)      # There should be 3 carts
            
#             # Check the cart to see that it's empty


#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response)
#             raise


# ########################
# # PURCHASES CLIENT TEST
# ########################

# #####################
# # RETRIEVE PURCHASES
# #####################

# class RetrievePurchasesClientTest(TestCase):
#     '''
#     Test for retrieve user purchases
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)
#         self.product2 = Product.objects.get(pk=3)

#     def test_user_purchase_retrieve(self):
#         '''
#         Test for retrieving user purchases
#         '''

#         self.client.force_login(self.user)

#         # todo: refactor to come from the fixtures...

#         offer = Offer.objects.get(pk=2)

#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)

#         offer2 = Offer.objects.get(pk=3)

#         orderitem2 = OrderItem.objects.create(invoice = invoice, offer = offer2, quantity = 2)

#         purchase_1 = Purchase.objects.create(user = self.user, order_item = orderitem, product = self.product)

#         purchase_2 = Purchase.objects.create(user = self.user, order_item = orderitem2, product = self.product2)

#         check_data = [
#             {
#                 "sku": "JOS45RB1",
#                 "name": "Test Product",
#                 "price": "50.00",
#                 "quantity": 1,
#                 "start_date": None,
#                 "end_date": None,
#                 "status": 0
#             },
#             {
#                 "sku": "JOS45RB1",
#                 "name": "Test Product2",
#                 "price": "90.00",
#                 "quantity": 2,
#                 "start_date": None,
#                 "end_date": None,
#                 "status": 0
#             }
#         ]

#         uri = reverse('vendor-purchases-retrieve-api')

#         response = self.client.get(uri)

#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Return Response Code
#             self.assertEqual(response.data[0].keys(), check_data[0].keys())

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


# #####################
# # PAYMENT PROCESSING
# #####################

# class PaymentProcessingTest(TestCase):
#     '''
#     Tests for Payment Proccessing
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)

#     def test_payment_process(self):
        
#         self.client.force_login(self.user)
#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)

#         uri = reverse('vendor-payment-processing-api')
#         response = self.client.post(uri)

#         purchases = Purchase.objects.filter(user = self.user)
#         invoice_completed = Invoice.objects.get(id = invoice.id)
        
#         try:
#             self.assertEqual(response.status_code, 200)     # 200 -> Created Response Code
#             self.assertEqual(invoice_completed.status, 20)
#             self.assertEqual(purchases.count(), 1)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(response.data)
#             raise


# #####################
# # REFUND CLIENT TEST
# #####################

# class RefundClientTest(TestCase):
#     '''
#     Tests for refund endpoints
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)

#     def test_refund_request(self):
#         '''
#         Tests for requesting a refund
#         '''

#         self.client.force_login(self.user)

#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)

#         uri = reverse('vendor-payment-processing-api')
#         response = self.client.post(uri)

#         purchase = Purchase.objects.get(user = self.user, order_item = orderitem)

#         refund_uri = reverse('vendor-refund-requesting-api')

#         data = {
#             "purchase": purchase.id,
#             "reason": "wrong description"
#         }

#         refund_response = self.client.post(refund_uri, data)

#         try:
#             self.assertEqual(refund_response.status_code, 200)     # 200 -> Created Response Code
#             self.assertEqual(Purchase.objects.get(user = self.user, order_item = orderitem).status, 20)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(refund_response.data)
#             raise


#     def test_refund_issue(self):
#         '''
#         Tests for issuing a refund
#         '''

#         self.client.force_login(self.user)

#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)

#         uri = reverse('vendor-payment-processing-api')
#         response = self.client.post(uri)

#         purchase = Purchase.objects.get(user = self.user, order_item = orderitem)

#         refund_uri = reverse('vendor-refund-requesting-api')

#         data = {
#             "purchase": purchase.id,
#             "reason": "wrong description"
#         }

#         refund_response = self.client.post(refund_uri, data)

#         refund = Refund.objects.get(purchase = purchase)

#         refund_issue_uri = reverse('vendor-refund-issue-api', kwargs={'id': refund.id})

#         refund_issue_response = self.client.patch(refund_issue_uri)

#         try:
#             self.assertEqual(refund_response.status_code, 200)     # 200 -> Created Response Code
#             self.assertEqual(Purchase.objects.get(user = self.user, order_item = orderitem).status, 30)
#             self.assertEqual(Refund.objects.get(purchase = purchase).accepted, True)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(refund_issue_response.data)
#             raise


# #####################
# #####################
# # MODEL CLIENT TESTS
# #####################
# #####################

# ###################
# # OFFER MODEL TEST
# ###################

# class OfferModelTest(TestCase):
#     '''
#     Test for Offer Model Test
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.product = Product.objects.get(pk=4)


#     def test_price_object_created(self):

#         offer = Offer.objects.create(product=self.product, msrp = 80)
#         price_object_count = offer.sale_price.all().count()

#         try:
#             self.assertEqual(price_object_count, 1)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(offer)
#             raise


#     def test_current_price(self):

#         offer = Offer.objects.create(product=self.product, msrp = 80)
#         price = Price.objects.create(offer = offer, cost = 90, priority=2, start_date = timezone.now(), end_date = timezone.now() + timezone.timedelta(days=1))

#         try:
#             self.assertEqual(offer.current_price(), offer.sale_price.all()[0].cost)

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             print(offer)
#             print(offer.current_price())
#             raise


# ###################
# # PRICE MODEL TEST
# ###################

# class PriceModelTest(TestCase):
#     '''
#     Test for Price Model Test
#     '''

#     # fixtures = ['unittest']

#     def setUp(self):
#         pass


# #####################
# # INVOICE MODEL TEST
# #####################

# class InvoiceModelTest(TestCase):
#     '''
#     Test for Invoice Model Test
#     '''

#     # fixtures = ['unittest']

#     def setUp(self):
#         pass


# #######################
# # ORDERITEM MODEL TEST
# #######################

# class OrderItemModelTest(TestCase):
#     '''
#     Test for OrderItem Model Test
#     '''

#     fixtures = ['unittest']

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.get(pk=2)
#         self.product = Product.objects.get(pk=4)

#     def test_order_item_total_retrieve(self):
#         '''
#         Test for retrieving OrderItem total based on the price and  quantity
#         '''

#         offer = Offer.objects.get(pk=2)
#         invoice = Invoice.objects.create(user = self.user, ordered_date = timezone.now())
#         orderitem = OrderItem.objects.create(invoice = invoice, offer = offer)

#         try:
#             self.assertEqual(orderitem.total, (orderitem.price * orderitem.quantity))

#         except:     # Only print results if there is an error, but continue to raise the error for the testing tool
#             print("")
#             # print(orderitem.price.all())
#             print(orderitem.quantity)
#             raise


# #######################
# # PURCHASES MODEL TEST
# #######################

# class PurchasesModelTest(TestCase):
#     '''
#     Test for Purchases Model Test
#     '''

#     # fixtures = ['unittest']

#     def setUp(self):
#         pass
