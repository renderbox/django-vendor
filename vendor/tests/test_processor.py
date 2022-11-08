from core.models import Product
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.utils import timezone
from django.urls import reverse
from django.test import TestCase, Client, tag

from unittest import skipIf
from random import randrange, choice
from siteconfigs.models import SiteConfigModel
from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.models import Invoice, Payment, Offer, Price, Receipt, CustomerProfile, OrderItem, Subscription
from vendor.models.choice import PurchaseStatus, InvoiceStatus, SubscriptionStatus
from vendor.processors import PaymentProcessorBase, AuthorizeNetProcessor, StripeProcessor
###############################
# Test constants
###############################

User = get_user_model()


class BaseProcessorTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.site = Site.objects.get(pk=1)
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.existing_invoice = Invoice.objects.get(pk=1)
        self.base_processor = PaymentProcessorBase(self.site, self.existing_invoice)
        self.subscription_offer = Offer.objects.get(pk=4)
        self.hamster_wheel = Offer.objects.get(pk=3)
        self.form_data = {
            'billing_address_form': {
                'billing-name': 'Home',
                'billing-company': 'Whitemoon Dreams',
                'billing-country': '840',
                'billing-address_1': '221B Baker Street',
                'billing-address_2': '',
                'billing-locality': 'Marylebone',
                'billing-state': 'California',
                'billing-postal_code': '90292'
            },
            'credit_card_form': {
                'full_name': 'Bob Ross',
                'card_number': '5424000000000015',
                'expire_month': '12',
                'expire_year': '2030',
                'cvv_number': '900',
                'payment_type': '10'
            }
        }

    def test_base_processor_init_fail(self):
        with self.assertRaises(TypeError):
            base_processor = PaymentProcessorBase()

    def test_base_processor_init_success(self):
        base_processor = PaymentProcessorBase(self.site, self.existing_invoice)

        self.assertEquals('PaymentProcessorBase', base_processor.provider)
        self.assertIsNotNone(base_processor.invoice)

    def test_create_payment_model_success(self):
        self.base_processor.set_billing_address_form_data(self.form_data['billing_address_form'], BillingAddressForm)
        self.base_processor.set_payment_info_form_data(self.form_data['credit_card_form'], CreditCardForm)
        self.base_processor.is_data_valid()
        self.base_processor.create_payment_model()

        self.assertIsNotNone(self.base_processor.payment)

    def test_save_payment_transaction_success(self):
        payment_success = True
        transaction_id = '1423wasd'

        self.base_processor.set_billing_address_form_data(self.form_data['billing_address_form'], BillingAddressForm)
        self.base_processor.set_payment_info_form_data(self.form_data['credit_card_form'], CreditCardForm)
        self.base_processor.is_data_valid()
        self.base_processor.create_payment_model()
        self.base_processor.transaction_succeeded = payment_success
        self.base_processor.transaction_id = transaction_id
        self.base_processor.save_payment_transaction_result()

        self.assertIsNotNone(self.base_processor.payment)
        self.base_processor.payment.refresh_from_db()

        self.assertTrue(self.base_processor.payment.success)
        self.assertEquals(self.base_processor.payment.transaction, transaction_id)
        self.assertIn('payment_info', self.base_processor.payment.result)

    def test_update_invoice_status_success(self):
        self.base_processor.transaction_succeeded = True
        self.base_processor.update_invoice_status(InvoiceStatus.COMPLETE)

        self.assertEquals(InvoiceStatus.COMPLETE, self.base_processor.invoice.status)

    def test_update_invoice_status_fails(self):
        self.base_processor.update_invoice_status(InvoiceStatus.COMPLETE)

        self.assertNotEquals(InvoiceStatus.COMPLETE, self.base_processor.invoice.status)

    def test_create_receipt_by_term_type_subscription(self):
        self.base_processor.invoice.add_offer(self.subscription_offer)
        self.base_processor.invoice.save()

        order_item_subscription = self.base_processor.invoice.order_items.get(offer__pk=4)
        self.base_processor.payment = Payment.objects.get(pk=1)
        
        self.base_processor.subscription_id = "123"
        self.base_processor.create_subscription_model()
        self.base_processor.create_receipt_by_term_type(order_item_subscription, order_item_subscription.offer.terms)

        self.assertIsNotNone(self.base_processor.subscription)
        self.assertIsNotNone(self.base_processor.receipt.subscription)

    def test_create_receipt_by_term_type_perpetual(self):
        self.base_processor.invoice.save()
        perpetual_order_item = self.base_processor.invoice.order_items.get(offer__pk=1)

        self.base_processor.payment = Payment.objects.get(pk=1)
        self.base_processor.create_receipt_by_term_type(perpetual_order_item, perpetual_order_item.offer.terms)

        self.assertIsNone(self.base_processor.receipt.subscription)

    # def test_create_receipt_by_term_type_one_time_use(self):
        # raise NotImplementedError()

    def test_create_receipts_success(self):
        self.base_processor.invoice.status = InvoiceStatus.COMPLETE
        self.base_processor.payment = Payment.objects.get(pk=1)
        self.base_processor.create_receipts(self.base_processor.invoice.order_items.all())

        self.assertEquals(Receipt.objects.all().count(), sum([ order_item.receipts.all().count() for order_item in self.base_processor.invoice.order_items.all() ]))

    # def test_update_subscription_receipt_success(self):
    #     subscription_id = 123456789
    #     self.base_processor.invoice.add_offer(self.subscription_offer)
    #     self.base_processor.invoice.save()
    #     self.base_processor.invoice.status = InvoiceStatus.COMPLETE
    #     self.base_processor.payment = Payment.objects.get(pk=1)
    #     self.base_processor.create_receipts(self.base_processor.invoice.order_items.all())

    #     subscription_list = self.existing_invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION)
    #     subscription = subscription_list[0]

    #     self.base_processor.update_subscription_receipt(subscription, subscription_id, PurchaseStatus.SETTLED)
    #     receipt = Receipt.objects.get(meta__subscription_id=subscription_id)

    #     self.assertIsNotNone(receipt)
    #     self.assertEquals(subscription_id, receipt.meta['subscription_id'])

    def test_amount_success(self):
        self.existing_invoice.update_totals()
        self.assertEquals(self.existing_invoice.total, self.base_processor.amount())

    def test_amount_without_subscriptions_success(self):
        self.base_processor.invoice.add_offer(self.subscription_offer)

        price = Price()
        price.offer = self.subscription_offer
        price.cost = 25
        price.start_date = timezone.now() - timedelta(days=1)
        price.save()
        self.assertNotEquals(self.existing_invoice.total, self.base_processor.amount_without_subscriptions())

    def test_get_transaction_id_success(self):
        self.base_processor.payment = Payment.objects.get(pk=1)
        self.assertIn(str(settings.SITE_ID), self.base_processor.get_transaction_id())
        self.assertIn(str(self.existing_invoice.profile.pk), self.base_processor.get_transaction_id())
        self.assertIn(str(self.existing_invoice.pk), self.base_processor.get_transaction_id())

    def test_set_billing_address_form_data_fail(self):
        with self.assertRaises(TypeError):
            self.base_processor.set_billing_address_form_data(self.form_data)

    def test_set_billing_address_form_data_success(self):
        self.base_processor.set_billing_address_form_data(self.form_data['billing_address_form'], BillingAddressForm)

        self.assertIsNotNone(self.base_processor.billing_address)
        self.assertIn(self.form_data['billing_address_form']['billing-address_1'], self.base_processor.billing_address.data['billing-address_1'])

    def test_set_payment_info_form_data_fail(self):
        with self.assertRaises(TypeError):
            self.base_processor.set_payment_info_form_data(self.form_data)

    def test_set_payment_info_form_data_success(self):
        self.base_processor.set_payment_info_form_data(self.form_data['credit_card_form'], CreditCardForm)

        self.assertIsNotNone(self.base_processor.payment_info)
        self.assertIn(self.form_data['credit_card_form']['cvv_number'], self.base_processor.payment_info.data['cvv_number'])

    def test_get_checkout_context_success(self):
        context = self.base_processor.get_checkout_context()
        self.assertIn('invoice', context)

    def test_free_payment_success(self):
        customer = CustomerProfile.objects.get(pk=2)
        invoice = Invoice(profile=customer)
        invoice.save()
        invoice.add_offer(Offer.objects.get(pk=8))

        base_processor = PaymentProcessorBase(invoice.site, invoice)

        base_processor.set_billing_address_form_data(self.form_data['billing_address_form'], BillingAddressForm)
        base_processor.set_payment_info_form_data(self.form_data['credit_card_form'], CreditCardForm)

        base_processor.authorize_payment()

        self.assertTrue(invoice.payments.count())
        self.assertTrue(customer.receipts.count())

    def test_renew_subscription(self):
        subscription = Subscription.objects.get(pk=1)
        submitted_datetime = timezone.now()

        invoice = Invoice.objects.create(
            profile=subscription.profile,
            site=subscription.profile.site,
            ordered_date=submitted_datetime,
            status=InvoiceStatus.COMPLETE
        )
        invoice.add_offer(subscription.receipts.first().order_item.offer)
        invoice.save()

        transaction_id = timezone.now().strftime("%Y-%m-%d_%H-%M-%S-Manual-Renewal")

        base_processor = PaymentProcessorBase(invoice.site, invoice)
        base_processor.renew_subscription(subscription, transaction_id, PurchaseStatus.CAPTURED)

        self.assertTrue(subscription.profile.has_product(subscription.receipts.last().products.all()))

    def test_subscription_price_update_success(self):
        subscription = Subscription.objects.get(pk=1)
        offer = Offer.objects.get(pk=4)
        price = Price.objects.create(offer=offer, cost=89.99, currency='usd', start_date=timezone.now())
        offer.prices.add(price)

        processor = PaymentProcessorBase(subscription.profile.site)
        processor.subscription_update_price(subscription, price, self.user)

        subscription.refresh_from_db()
        self.assertIn('price_update', subscription.meta)

    # def test_get_header_javascript_success(self):
    #     raise NotImplementedError()

    # def test_get_javascript_success(self):
    #     raise NotImplementedError()

    # def test_get_template_success(self):
    #     raise NotImplementedError()

    # def test_authorize_payment_success(self):
    #     raise NotImplementedError()

    # def test_pre_authorization_success(self):
    #     raise NotImplementedError()

    # def test_process_payment_success(self):
    #     raise NotImplementedError()

    # def test_post_authorization_success(self):
    #     raise NotImplementedError()

    # def test_capture_payment_success(self):
    #     raise NotImplementedError()

    # def test_subscription_payment_success(self):
    #     raise NotImplementedError()

    # def test_subscription_cancel_success(self):
    #     raise NotImplementedError()

    # def test_refund_payment_success(self):
    #     raise NotImplementedError()


class SupportedProcessorsSetupTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.invoice = Invoice.objects.get(pk=1)
        self.site = Site.objects.get(pk=1)

    def test_configured_processor_setup(self):
        """
        Test the initialized of the PaymentProcessor defined in the setting file
        """
        try:
            processor = PaymentProcessorBase(self.site, self.invoice)
        except Exception:
            print("Warning PaymentProcessor defined in settings file did not pass init")
        finally:
            pass

    def test_authorize_net_init(self):
        try:
            if not (settings.AUTHORIZE_NET_TRANSACTION_KEY and settings.AUTHORIZE_NET_API_ID):
                raise ValueError(
                "Missing Authorize.net keys in settings: AUTHORIZE_NET_TRANSACTION_KEY and/or AUTHORIZE_NET_API_ID")
            processor = AuthorizeNetProcessor(self.site, self.invoice)
        except Exception:
            print("AuthorizeNetProcessor did not initalized correctly")
        finally:
            pass

    # def test_stripe_init(self):
        # raise NotImplementedError()

