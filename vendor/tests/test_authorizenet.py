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
from vendor.models.choice import PurchaseStatus, InvoiceStatus
from vendor.processors import PaymentProcessorBase, AuthorizeNetProcessor
from vendor.processors.authorizenet import create_subscription_model_form_past_receipts


# @skipIf(True, "Webhook tests are highly dependent on data in Authroizenet and local data.")
@tag('external')
@skipIf((settings.AUTHORIZE_NET_API_ID is None) or (settings.AUTHORIZE_NET_TRANSACTION_KEY is None), "Authorize.Net enviornment variables not set, skipping tests")
class AuthorizeNetProcessorTests(TestCase):

    fixtures = ['user', 'unit_test']

    VALID_CARD_NUMBERS = [
        '370000000000002',
        '6011000000000012',
        '3088000000000017',
        '38000000000006',
        '4007000000027',
        '4012888818888',
        '4111111111111111',
        '5424000000000015',
        '2223000010309703',
        '2223000010309711'
    ]

    def setup_processor_site_config(self):
        self.processor_site_config = SiteConfigModel()
        self.processor_site_config.site = self.existing_invoice.site
        self.processor_site_config.key = 'vendor.config.PaymentProcessorSiteConfig'
        self.processor_site_config.value = {"payment_processor": "authorizenet.AuthorizeNetProcessor"}
        self.processor_site_config.save()

    def setup_user_client(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def setup_existing_invoice(self):
        t_shirt = Product.objects.get(pk=1)
        t_shirt.meta['msrp']['usd'] = randrange(1, 1000)
        t_shirt.save()
        self.form_data = {
            'billing_address_form': {
                'billing-name': 'Home',
                'billing-company': 'Whitemoon Dreams',
                'billing-country': '840',
                'billing-address_1': '221B Baker Street',
                'billing-address_2': '',
                'billing-locality': 'Marylebone',
                'billing-state': 'California',
                'billing-postal_code': '90292'},
            'credit_card_form': {
                'full_name': 'Bob Ross',
                'card_number': '5424000000000015',
                'expire_month': '12',
                'expire_year': '2030',
                'cvv_number': '900',
                'payment_type': '10'}
        }
        self.subscription_offer = Offer.objects.get(pk=6)
        price = Price.objects.get(pk=1)
        price.cost = randrange(1, 1000)
        price.priority = 10
        price.save()
        subscription_price = Price.objects.get(pk=9)
        subscription_price.cost = randrange(1, 1000)
        price.priority = 10
        subscription_price.priority = 10
        subscription_price.save()
        self.existing_invoice.update_totals()

    def setUp(self):
        self.setup_user_client()
        self.existing_invoice = Invoice.objects.get(pk=1)
        self.setup_processor_site_config()
        self.setup_existing_invoice()
        self.site = self.processor_site_config.site
        self.processor = AuthorizeNetProcessor(self.site, self.existing_invoice)


    ##########
    # Processor Initialization Tests
    ##########
    def test_environment_variables_set(self):
        self.assertIsNotNone(settings.AUTHORIZE_NET_TRANSACTION_KEY)
        self.assertIsNotNone(settings.AUTHORIZE_NET_API_ID)

    def test_processor_initialization_success(self):
        self.assertEquals(self.processor.provider, 'AuthorizeNetProcessor')
        self.assertIsNotNone(self.processor.invoice)
        self.assertIsNotNone(self.processor.merchant_auth)
        self.assertIsNotNone(self.processor.merchant_auth.transactionKey)
        self.assertIsNotNone(self.processor.merchant_auth.name)

    ##########
    # Checkout and Payment Transaction Tests
    ##########
    def test_get_checkout_context(self):
        context = {}

        context = self.processor.get_checkout_context()

        self.assertIn('invoice', context)
        self.assertIn('credit_card_form', context)
        self.assertIn('billing_address_form', context)

    def test_process_payment_transaction_success(self):
        """
        By passing in the invoice, setting the payment info and billing
        address, process the payment and make sure it succeeds.
        """
        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)
        
        self.processor.invoice.total = randrange(1, 1000)
        for recurring_order_items in self.processor.invoice.get_recurring_order_items():
            self.processor.invoice.remove_offer(recurring_order_items.offer)

        self.processor.authorize_payment()

        print(self.processor.transaction_message)
        self.assertIsNotNone(self.processor.payment)
        self.assertTrue(self.processor.payment.success)
        self.assertEquals(InvoiceStatus.COMPLETE, self.processor.invoice.status)

    def test_process_payment_transaction_fail_invalid_card(self):
        """
        Simulates a payment transaction for a reqeust.POST, with the payment and
        billing information. The test send an invalid card number to test the
        transation fails
        """
        self.form_data['credit_card_form']['card_number'] = '5424000000015'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)
        self.processor.authorize_payment()

        self.assertIsNone(self.processor.payment)
        self.assertFalse(self.processor.transaction_submitted)
        self.assertEquals(InvoiceStatus.CART, self.processor.invoice.status)

    def test_process_payment_transaction_fail_invalid_expiration(self):
        """
        Simulates a payment transaction for a reqeust.POST, with the payment and
        billing information. The test send an invalid expiration date to test the
        transation fails.
        """
        self.form_data['credit_card_form']['expire_month'] = str(timezone.now().month)
        self.form_data['credit_card_form']['expire_year'] = str(timezone.now().year - 1)

        self.processor.set_billing_address_form_data(self.form_data['billing_address_form'], BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data['credit_card_form'], CreditCardForm)

        self.processor.authorize_payment()

        self.assertIsNone(self.processor.payment)
        self.assertFalse(self.processor.transaction_submitted)
        self.assertEquals(InvoiceStatus.CART, self.processor.invoice.status)

    ##########
    # CVV Tests
    # Reference: Test Guide: https://developer.authorize.net/hello_world/testing_guide.html
    ##########
    def test_process_payment_fail_cvv_no_match(self):
        """
        Check a failed transaction due to cvv number does not match card number.
        CVV: 901
        """
        self.form_data['credit_card_form']['cvv_number'] = '901'
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        results = ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result])
        if 'The merchant does not accept this type of credit card' in results:
            print(f'Skipping test test_process_payment_fail_cvv_no_match because merchant does not accept card')
        else:
            self.assertIn("'cvvResultCode': 'N'", results)

    def test_process_payment_fail_cvv_should_not_be_on_card(self):
        """
        Check a failed transaction due to cvv number does not match card number.
        CVV: 902
        """
        self.form_data['credit_card_form']['cvv_number'] = '902'
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        results = ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result])
        if 'The merchant does not accept this type of credit card' in results:
            print(f'Skipping test test_process_payment_fail_cvv_should_not_be_on_card because merchant does not accept card')
        else:
            self.assertIn("'cvvResultCode': 'S'", results)

    def test_process_payment_fail_cvv_not_certified(self):
        """
        Check a failed transaction due to cvv number does not match card number.
        Test Guide: https://developer.authorize.net/hello_world/testing_guide.html
        CVV: 903
        """
        self.form_data['credit_card_form']['cvv_number'] = '903'
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        results = ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result])
        if 'The merchant does not accept this type of credit card' in results:
            print(f'Skipping test test_process_payment_fail_cvv_not_certified because merchant does not accept card')
        else:
            self.assertIn("'cvvResultCode': 'U'", results)

    def test_process_payment_fail_cvv_not_processed(self):
        """
        Check a failed transaction due to cvv number is not processed.
        CVV: 904
        """
        self.form_data['credit_card_form']['cvv_number'] = '904'
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        results = ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result])
        if 'The merchant does not accept this type of credit card' in results:
            print(f'Skipping test test_process_payment_fail_cvv_not_processed because merchant does not accept card')
        else:
            self.assertIn("'cvvResultCode': 'P'", results)

    ##########
    # AVS Tests
    # Reference: https://support.authorize.net/s/article/What-Are-the-Different-Address-Verification-Service-AVS-Response-Codes
    ##########
    def test_process_payment_avs_addr_match_zipcode_no_match(self):
        """
        A = Street Address: Match -- First 5 Digits of ZIP: No Match
        Postal Code: 46201
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46201'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'A'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    def test_process_payment_avs_service_error(self):
        """
        E = AVS Error
        Postal Code: 46203
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46203'
        self.form_data['credit_card_form']['card_number'] = '2223000010309711'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'E'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    def test_process_payment_avs_non_us_card(self):
        """
        G = Non U.S. Card Issuing Bank
        Postal Code: 46204
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46204'
        self.form_data['credit_card_form']['card_number'] = '4007000000027'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'G'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    def test_process_payment_avs_addr_no_match_zipcode_no_match(self):
        """
        N = Street Address: No Match -- First 5 Digits of ZIP: No Match
        Postal Code: 46205
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46205'
        self.form_data['credit_card_form']['card_number'] = '2223000010309711'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'N'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    def test_process_payment_avs_retry_service_unavailable(self):
        """
        R = Retry, System Is Unavailable
        Postal Code: 46207
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46207'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'R'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))
            self.assertFalse(self.processor.payment.success)
            self.assertEquals(InvoiceStatus.CART, self.processor.invoice.status)

    def test_process_payment_avs_not_supported(self):
        """
        S = AVS Not Supported by Card Issuing Bank
        Postal Code: 46208
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46208'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'S'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    def test_process_payment_avs_addrs_info_unavailable(self):
        """
        U = Address Information For This Cardholder Is Unavailable
        Postal Code: 46209
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46209'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'U'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    def test_process_payment_avs_addr_no_match_zipcode_match_9_digits(self):
        """
        W = Street Address: No Match -- All 9 Digits of ZIP: Match
        Postal Code: 46211
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46211'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'W'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    def test_process_payment_avs_addr_match_zipcode_match(self):
        """
        X = Street Address: Match -- All 9 Digits of ZIP: Match
        Postal Code: 46214
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46214'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'X'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    def test_process_payment_avs_addr_no_match_zipcode_match_5_digits(self):
        """
        Z = Street Address: No Match - First 5 Digits of ZIP: Match
        Postal Code: 46217
        """
        self.form_data['billing_address_form']['billing-postal_code'] = '46217'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()

        self.assertIsNotNone(self.processor.payment)
        if 'duplicate' in Payment.objects.filter(invoice=self.existing_invoice).first().result.get("raw", ""):
            print("Duplicate transaction registered by Payment Gateway Skipping Tests")
        else:
            self.assertIn("'avsResultCode': 'Z'", ''.join([p.result.get('raw') for p in Payment.objects.filter(invoice=self.existing_invoice, subscription=None) if 'raw' in p.result]))

    ##########
    # Refund Transactin Tests
    ##########
    def test_refund_success(self):
        """
        In order for this test to pass a transaction has to be settled first. The settlement process
        takes effect once a day. It is defined in the Sandbox in the cut-off time.
        The test will get a settle payment and test refund transaction.
        """
        # Get Settled payment
        start_date, end_date = (timezone.now() - timedelta(days=31)), timezone.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        if not batch_list:
            print("No Transactions to refund Skipping\n")
            return

        for batch in batch_list:
            transaction_list = self.processor.get_transaction_batch_list(str(batch.batchId))
            successfull_transactions = [ t for t in transaction_list if t['transactionStatus'] == 'settledSuccessfully' ]
            if len(successfull_transactions) > 0:
                break

        if not successfull_transactions:
            print("No Transactions to refund Skipping\n")
            return

        random_index = randrange(0, len(successfull_transactions))
        payment = Payment()
        # payment.amount = transaction_detail.authAmount.pyval
        # Hard coding minimum amount so the test can run multiple times.
        payment.amount = 0.01
        payment.invoice = self.existing_invoice
        payment.transaction = successfull_transactions[random_index].transId.text
        payment.result["raw"] = str({ 'accountNumber': successfull_transactions[random_index].accountNumber.text})
        payment.profile = CustomerProfile.objects.get(pk=1)
        payment.save()
        self.processor.payment = payment

        self.processor.refund_payment(payment)
        print(f'\ntest_refund_success\nMessage: {self.processor.transaction_message}\nResponse: {self.processor.transaction_response}\n')
        if 'error_code' in self.processor.transaction_message:
            if self.processor.transaction_message['error_code'] == 8:
                print("The credit card has expired. Skipping\n")
                return
        self.assertEquals(PurchaseStatus.REFUNDED, payment.status)

    def test_refund_fail_invalid_account_number(self):
        """
        Checks for transaction_submitted fail because the account number does not match the payment transaction settled.
        """
        status_before_transaction = self.existing_invoice.status

        # Get Settled payment
        start_date, end_date = (timezone.now() - timedelta(days=31)), timezone.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        if not batch_list:
            print("No Transactions to refund Skipping\n")
            return
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.invoice = self.existing_invoice
        payment.amount = 0.01
        payment.transaction = transaction_list[-1].transId.text
        payment.result["raw"] = str({ 'accountNumber': '6699'})
        payment.profile = CustomerProfile.objects.get(pk=1)
        payment.save()
        self.processor.payment = payment

        self.processor.refund_payment(payment)

        self.assertFalse(self.processor.transaction_submitted)
        self.assertEquals(self.processor.invoice.status, status_before_transaction)

    def test_refund_fail_invalid_amount(self):
        """
        Checks for transaction_submitted fail because the amount exceeds the payment transaction settled.
        """
        status_before_transaction = self.existing_invoice.status

        # Get Settled payment
        start_date, end_date = (timezone.now() - timedelta(days=31)), timezone.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        if not batch_list:
            print("No Transactions to refund Skipping\n")
            return
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.invoice = self.existing_invoice
        payment.amount = 1000000.00
        payment.transaction = transaction_list[-1].transId.text
        payment.result["raw"] = str({ 'accountNumber': transaction_list[-1].accountNumber.text})
        payment.profile = CustomerProfile.objects.get(pk=1)
        payment.save()
        self.processor.payment = payment

        self.processor.refund_payment(payment)

        self.assertFalse(self.processor.transaction_submitted)
        self.assertEquals(self.processor.invoice.status, status_before_transaction)

    def test_refund_fail_invalid_transaction_id(self):
        """
        Checks for transaction_submitted fail because the transaction id does not match
        """
        self.processor = AuthorizeNetProcessor(self.site, self.existing_invoice)
        status_before_transaction = self.existing_invoice.status

        # Get Settled payment
        start_date, end_date = (timezone.now() - timedelta(days=31)), timezone.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        if not batch_list:
            print("No Transactions to refund Skipping\n")
            return
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.invoice = self.existing_invoice
        payment.amount = 0.01
        payment.transaction = '111222333412'
        payment.result["raw"] = str({ 'accountNumber': transaction_list[-1].accountNumber.text})
        payment.profile = CustomerProfile.objects.get(pk=1)
        payment.save()
        self.processor.payment = payment

        self.processor.refund_payment(payment)

        self.assertFalse(self.processor.transaction_submitted)
        self.assertEquals(self.processor.invoice.status, status_before_transaction)

    ##########
    # Customer Payment Profile Transaction Tests
    # ##########
    # def test_create_customer_payment_profile(self):
        # raise NotImplementedError()

    # def test_update_customer_payment_profile(self):
        # raise NotImplementedError()

    # def test_get_customer_payment_profile(self):
        # raise NotImplementedError()

    # def test_get_customer_payment_profile_list(self):
        # raise NotImplementedError()

    ##########
    # Subscription Transaction Tests
    ##########
    def test_create_subscription_success(self):
        """
        Test a successfull subscription enrollment.
        """
        self.existing_invoice.add_offer(self.subscription_offer)
        price = Price()
        price.offer = self.subscription_offer
        price.cost = randrange(1, 1000)
        price.priority = 10
        price.start_date = timezone.now() - timedelta(days=1)
        price.save()
        self.existing_invoice.update_totals()
        self.existing_invoice.save()

        self.processor = AuthorizeNetProcessor(self.site, self.existing_invoice)

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.authorize_payment()

        # print(self.processor.transaction_message)
        self.assertTrue(self.processor.transaction_submitted)
        self.assertIn('subscriptionId', self.processor.transaction_response['raw'])
        self.assertIsNotNone(self.processor.subscription)
        self.assertFalse(self.processor.payment.transaction)
        self.assertFalse(self.processor.receipt.transaction)

    def test_subscription_update_payment(self):
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)
        subscription_list = self.processor.get_list_of_subscriptions()

        if not len(subscription_list):
            print("No subscriptions, Skipping Test")
            return

        active_subscriptions = [ s for s in subscription_list if s['status'] == 'active' ]

        dummy_receipt = Receipt(order_item=OrderItem.objects.get(pk=2))
        dummy_receipt.profile = CustomerProfile.objects.get(pk=1)
        dummy_receipt.transaction = active_subscriptions[-1].id.pyval
        dummy_payment = Payment.objects.create(invoice=self.existing_invoice,
                                               transaction=dummy_receipt.transaction,
                                               profile=dummy_receipt.profile,
                                               success=True,
                                               amount=dummy_receipt.order_item.invoice.total)
        dummy_payment.result['account_number'] = ""
        dummy_payment.result['account_type'] = ""
        dummy_payment.profile = CustomerProfile.objects.get(pk=1)
        dummy_payment.save()

        if active_subscriptions:
            self.processor.set_payment_info_form_data(self.form_data['credit_card_form'], CreditCardForm)
            self.processor.subscription_update_payment(dummy_receipt)
            dummy_payment.refresh_from_db()
            print(f'\ntest_subscription_update_payment\nMessage: {self.processor.transaction_message}\nResponse: {self.processor.transaction_response}\nSubscription ID: {dummy_receipt.transaction}\n')
            print(f"Update Card number: {self.form_data['credit_card_form']['card_number'][-4:]}")
            if 'E00027' in str(self.processor.transaction_message):
                print("Merchant does not accept this card. Skipping test")
            else:
                self.assertTrue(self.processor.transaction_submitted)
                self.assertEquals(dummy_payment.result['account_number'][-4:], self.form_data['credit_card_form']['card_number'][-4:])
        else:
            print("No active Subscriptions, Skipping Test")

    def test_cancel_subscription_success(self):
        subscription_list = self.processor.get_list_of_subscriptions()
        if not len(subscription_list):
            print("No subscriptions, Skipping Test")
            return
        active_subscriptions = [ s for s in subscription_list if s['status'] == 'active' ]
        dummy_receipt = Receipt(order_item=OrderItem.objects.get(pk=2))
        dummy_receipt.profile = CustomerProfile.objects.get(pk=1)
        dummy_receipt.transaction = active_subscriptions[0].id.pyval

        dummy_subscription = Subscription.objects.create(
            gateway_id=active_subscriptions[0].id.pyval,
            profile=CustomerProfile.objects.get(pk=1),
        )
        if active_subscriptions:
            self.processor.subscription_cancel(dummy_subscription)
            self.assertTrue(self.processor.transaction_submitted)
        else:
            print("No active Subscriptions, Skipping Test")

    def test_is_card_valid_fail(self):
        self.form_data['credit_card_form']['cvv_number'] = '901'
        self.existing_invoice.add_offer(self.subscription_offer)
        price = Price()
        price.offer = self.subscription_offer
        price.cost = randrange(1, 1000)
        price.priority = 10
        price.start_date = timezone.now() - timedelta(days=1)
        price.save()
        self.existing_invoice.save()
        self.processor = AuthorizeNetProcessor(self.site, self.existing_invoice)
        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)
        self.processor.is_data_valid()
        self.processor.create_payment_model()
        self.assertFalse(self.processor.is_card_valid())

    def test_is_card_valid_success(self):
        self.existing_invoice.add_offer(self.subscription_offer)
        price = Price()
        price.offer = self.subscription_offer
        price.cost = randrange(11, 1000)
        price.start_date = timezone.now() - timedelta(days=1)
        price.priority = 10
        price.save()
        self.existing_invoice.update_totals()
        self.existing_invoice.save()
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)
        self.processor = AuthorizeNetProcessor(self.site, self.existing_invoice)
        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)
        self.processor.is_data_valid()
        self.processor.create_payment_model()
        is_valid = self.processor.is_card_valid()
        print(f"Test is_card_valid_success\n")
        print(f"Transaction Submitted: {self.processor.transaction_submitted}")
        print(f"Transaction Response: {self.processor.transaction_response}")
        print(f"Transaction Msg: {self.processor.transaction_message}")
        if 'duplicate' in str(self.processor.transaction_message):
            print(f"Skipping Test test_is_card_valid_success because of duplicate")
            return None
        elif 'not accept this type of credit card' in str(self.processor.transaction_message):
            print(f"Skipping Test test_is_card_valid_success because of duplicate")
            return None
        else:
            self.assertTrue(is_valid)

    def test_subscription_price_update_success(self):
        subscription_list = self.processor.get_list_of_subscriptions()
        if not len(subscription_list):
            print("No subscriptions, Skipping Test")
            return None
        active_subscriptions = [ s for s in subscription_list if s['status'] == 'active' ]
        subscription_id = active_subscriptions[-1].id.pyval
        new_price = randrange(1, 1000)
        receipt = Receipt.objects.all().last()
        receipt.transaction = subscription_id
        receipt.save()
        if active_subscriptions:
            self.processor.subscription_update_price(receipt, new_price, self.user)
            print(f'\test_subscription_update_price\nMessage: {self.processor.transaction_message}\nResponse: {self.processor.transaction_response}\nSubscription ID: {receipt.transaction}\n')
            response = self.processor.subscription_info(receipt.transaction)
            self.assertTrue(self.processor.transaction_submitted)
            self.assertEqual(new_price, response.subscription.amount.pyval)
        else:
            print("No active Subscriptions, Skipping Test")

    # def test_create_subscription_model_form_past_receipts(self):
    #     create_subscription_model_form_past_receipts(self.site)

    ##########
    # Report details
    ##########
    def test_get_transaction_details(self):
        transaction_id = '60160039986'
        self.processor = AuthorizeNetProcessor(self.site, self.existing_invoice)
        transaction_detail = self.processor.get_transaction_detail(transaction_id)
        self.assertTrue(transaction_detail)

    def test_get_settled_transaction(self):
        start_date, end_date = (timezone.now() - timedelta(days=3)), timezone.now()
        settled_transactions = self.processor.get_settled_transactions(start_date, end_date)

        self.assertTrue(settled_transactions)
    ##########
    # Transaction View Tests
    ##########
    def test_view_checkout_account_success_code(self):
        response = self.client.get(reverse("vendor:checkout-account"))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Shipping Address')

    def test_view_checkout_payment_success_code(self):
        response = self.client.get(reverse("vendor:checkout-payment"))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Billing Address')

    def test_view_checkout_review_success_code(self):
        response = self.client.get(reverse("vendor:checkout-review"))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Review')

    def test_view_checkout_status_code_fail_no_login(self):
        client = Client()
        response = client.get(reverse("vendor:checkout-review"))

        self.assertEquals(response.status_code, 302)
        self.assertIn('login', response.url)

    ##########
    # Expiration Card Tests
    ##########
    def test_get_expiring_cards_fail(self):
        site = Site.objects.get(pk=1)
        processor = AuthorizeNetProcessor(site)

        processor.get_customer_id_for_expiring_cards("2022-6")  # should be in the format YYYY-MM

        self.assertFalse(processor.transaction_submitted)

    def test_get_expiring_cards_success(self):
        site = Site.objects.get(pk=1)
        processor = AuthorizeNetProcessor(site)

        ids = processor.get_customer_id_for_expiring_cards("2024-01")

        self.assertTrue(processor.transaction_submitted)
        self.assertTrue(ids)

    def test_get_expiring_cards_empty(self):
        site = Site.objects.get(pk=1)
        processor = AuthorizeNetProcessor(site)

        ids = processor.get_customer_id_for_expiring_cards("2020-01")

        self.assertTrue(processor.transaction_submitted)
        self.assertFalse(ids)

    def test_get_customer_email(self):
        site = Site.objects.get(pk=1)
        processor = AuthorizeNetProcessor(site)

        ids = processor.get_customer_id_for_expiring_cards("2023-01")
        emails = []

        for cp_id in ids:
            emails.append(processor.get_customer_email(cp_id))

        self.assertTrue(emails)
        
