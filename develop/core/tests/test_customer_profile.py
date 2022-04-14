from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from core.models import Product

from vendor.models import Offer, Price, Invoice, Receipt, CustomerProfile
from vendor.models.choice import PurchaseStatus, TermType


class ModelCustomerProfileTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.user = User(username='test', first_name='Bob', last_name='Ross', password='helloworld')
        self.user.save()
        self.customer_profile = CustomerProfile()
        self.customer_profile.user = User.objects.get(pk=2)
        self.customer_profile.save()

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

        self.assertEquals(count, customer_profile.invoices.first().order_items.count())

    def test_owns_product_true(self):
        receipt = Receipt.objects.get(pk=1)
        receipt.end_date = None
        receipt.save()
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
        self.customer_profile_existing.invoices.add(Invoice.objects.create(status=Invoice.InvoiceStatus.CHECKOUT, profile=self.customer_profile_existing))

        cart = self.customer_profile_existing.get_cart_or_checkout_cart()

        self.assertEqual(cart.status, Invoice.InvoiceStatus.CHECKOUT)

    def test_get_cart_items_count(self):
        invoice = Invoice.objects.get(pk=1)
        self.assertEqual(invoice.order_items.count(), self.customer_profile_existing.get_cart_items_count())

    def test_get_cart_items_count_empty(self):
        self.assertEqual(0, self.customer_profile.get_cart_items_count())

    def test_get_recurring_receipts(self):
        cart = self.customer_profile.get_cart_or_checkout_cart()
        subscription_offer = Offer.objects.get(pk=5)
        cart.add_offer(subscription_offer)

        receipt = Receipt(profile=self.customer_profile,
                          order_item=cart.order_items.first(),
                          start_date=timezone.now(),
                          transaction="123",
                          status=PurchaseStatus.COMPLETE)
        receipt.save()
        self.assertEqual(1, len(self.customer_profile.get_recurring_receipts()))
        self.assertEqual(0, len(self.customer_profile.get_one_time_transaction_receipts()))

    def test_get_one_time_transaction_receipts(self):
        cart = self.customer_profile.get_cart_or_checkout_cart()
        offer = Offer.objects.get(pk=3)
        cart.add_offer(offer)

        receipt = Receipt(profile=self.customer_profile,
                          order_item=cart.order_items.first(),
                          start_date=timezone.now(),
                          transaction="123",
                          status=PurchaseStatus.COMPLETE)
        receipt.save()
        self.assertEqual(0, len(self.customer_profile.get_recurring_receipts()))
        self.assertEqual(1, len(self.customer_profile.get_one_time_transaction_receipts()))

    def test_has_previously_owned_products_true(self):
        cart = self.customer_profile.get_cart_or_checkout_cart()
        offer = Offer.objects.get(pk=3)
        cart.add_offer(offer)

        receipt = Receipt(profile=self.customer_profile,
                          order_item=cart.order_items.first(),
                          start_date=timezone.now(),
                          transaction="123",
                          status=PurchaseStatus.COMPLETE)
        receipt.save()
        receipt.products.add(offer.products.first())
        self.assertTrue(self.customer_profile.has_previously_owned_products(Product.objects.filter(pk=3)))

    def test_has_previously_owned_products_false(self):
        cart = self.customer_profile.get_cart_or_checkout_cart()

        self.assertFalse(self.customer_profile.has_previously_owned_products(Product.objects.filter(pk=3)))

    def test_get_completed_receipts(self):
        cart = self.customer_profile.get_cart_or_checkout_cart()
        offer = Offer.objects.get(pk=3)
        cart.add_offer(offer)

        receipt = Receipt(profile=self.customer_profile,
                          order_item=cart.order_items.first(),
                          start_date=timezone.now(),
                          transaction="123",
                          status=PurchaseStatus.COMPLETE)
        receipt.save()
        self.assertEqual(1, len(self.customer_profile.get_completed_receipts()))

    def test_get_completed_receipts_empty(self):
        cart = self.customer_profile.get_cart_or_checkout_cart()
        offer = Offer.objects.get(pk=3)
        cart.add_offer(offer)

        self.assertEqual(0, len(self.customer_profile.get_completed_receipts()))

    def test_get_products(self):
        self.assertFalse(self.customer_profile.get_all_customer_products())

    def test_get_active_offer_receipts_success(self):
        cart = self.customer_profile.get_cart_or_checkout_cart()
        offer = Offer.objects.get(pk=3)
        cart.add_offer(offer)

        receipt = Receipt(profile=self.customer_profile,
                          order_item=cart.order_items.first(),
                          start_date=timezone.now(),
                          transaction="123",
                          status=PurchaseStatus.COMPLETE)
        receipt.save()
        self.assertTrue(len(self.customer_profile.get_active_offer_receipts(offer)) > 0)

    def test_get_active_offer_receipts_empty(self):
        offer = Offer.objects.get(pk=3)
        self.assertTrue(len(self.customer_profile.get_active_offer_receipts(offer)) == 0)

    def test_get_active_products_none(self):
        receipt = Receipt.objects.get(pk=2)
        receipt.end_date = timezone.now()
        receipt.save()
        product = self.customer_profile_existing.get_active_products()
        self.assertFalse(len(product))

    def test_get_active_products(self):
        product = self.customer_profile_existing.get_active_products()
        self.assertTrue(len(product))

    def test_get_active_product_and_offer(self):
        product_offer = self.customer_profile_existing.get_active_product_and_offer()
        self.assertEqual(product_offer[0][0], Product.objects.get(pk=2))
        self.assertEqual(product_offer[0][1], Offer.objects.get(pk=2))

    def test_get_checkout_invoice_success(self):
        invoice_invalid_cart = Invoice()
        invoice_invalid_cart.status = Invoice.InvoiceStatus.CART
        invoice_invalid_cart.profile = self.customer_profile_existing
        invoice_invalid_cart.save()

        invoice = self.customer_profile_existing.get_cart_or_checkout_cart()

        self.assertEqual(1, self.customer_profile_existing.invoices.filter(status=Invoice.InvoiceStatus.CART, deleted=False).count())


class AddOfferToProfileView(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.customer_profile = CustomerProfile.objects.get(pk=1)
        self.free_offer = Offer.objects.create(name='Free Offer',
                                               start_date=timezone.now(),
                                               terms=TermType.MONTHLY_SUBSCRIPTION,
                                               term_details={ "term_units": 20,
                                                              "trial_occurrences": 1})
        price = Price.objects.create(offer=self.free_offer, cost=0, start_date=timezone.now())
        self.free_offer.products.add(Product.objects.get(pk=5))

    def test_view_cart_status_code(self):
        url = reverse('vendor_api:manager-profile-add-offer', kwargs={'uuid_profile': self.customer_profile.uuid, 'uuid_offer': self.free_offer.uuid})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_adds_free_product_to_profile_success(self):
        url = reverse('vendor_api:manager-profile-add-offer', kwargs={'uuid_profile': self.customer_profile.uuid, 'uuid_offer': self.free_offer.uuid})
        response = self.client.get(url)
        self.assertTrue(self.customer_profile.receipts.count())

    def test_adds_free_product_to_profile_fail(self):
        url = reverse('vendor_api:manager-profile-add-offer', kwargs={'uuid_profile': self.customer_profile.uuid, 'uuid_offer': Offer.objects.get(pk=2).uuid})
        response = self.client.get(url)
        self.assertFalse(self.customer_profile.receipts.count())

