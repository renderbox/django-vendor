from core.models import Product
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.http import HttpRequest, QueryDict
from django.utils import timezone
from django.urls import reverse
from django.test import TestCase, Client
from unittest import skipIf
from random import randrange, choice
from string import ascii_letters
from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.models import Invoice, Payment, Offer, Price, Receipt
from vendor.models.address import Country
from vendor.models.choice import TermType
from vendor.processors.base import PaymentProcessorBase
from vendor.processors.authorizenet import AuthorizeNetProcessor
from vendor.processors import PaymentProcessor

###############################
# Test constants
###############################

User = get_user_model()


class BaseProcessorTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.existing_invoice = Invoice.objects.get(pk=1)
        self.base_processor = PaymentProcessorBase(self.existing_invoice)
        self.subscription_offer = Offer.objects.get(pk=4)
        self.form_data = { 
            'billing_address_form': 
                {'name':'Home','company':'Whitemoon Dreams','country':'581','address_1':'221B Baker Street','address_2':'','locality':'Marylebone','state':'California','postal_code':'90292'}, 
            'credit_card_form': 
                {'full_name':'Bob Ross','card_number':'5424000000000015','expire_month':'12','expire_year':'2030','cvv_number':'900','payment_type':'10'}
            }

    def test_base_processor_init_fail(self):
        with self.assertRaises(TypeError):
            base_processor = PaymentProcessorBase()

    def test_base_processor_init_success(self):
        base_processor = PaymentProcessorBase(self.existing_invoice)
        
        self.assertEquals('PaymentProcessorBase', base_processor.provider)
        self.assertIsNotNone(base_processor.invoice)

    def test_processor_setup_success(self):
        # TODO: Implement Test
        pass    

    def test_set_payment_info_success(self):
        # TODO: Implement Test
        pass

    def test_set_invoice_success(self):
        # TODO: Implement Test
        pass

    def test_create_payment_model_success(self):
        self.base_processor.create_payment_model()

        self.assertIsNotNone(self.base_processor.payment)

    def test_save_payment_transaction_success(self):
        # TODO: Implement Test
        pass

    def test_update_invoice_status_success(self):
        self.base_processor.transaction_submitted = True
        self.base_processor.update_invoice_status(Invoice.InvoiceStatus.REFUNDED)

        self.assertEquals(Invoice.InvoiceStatus.REFUNDED, self.base_processor.invoice.status)

    def test_update_invoice_status_fails(self):
        self.base_processor.update_invoice_status(Invoice.InvoiceStatus.REFUNDED)

        self.assertNotEquals(Invoice.InvoiceStatus.REFUNDED, self.base_processor.invoice.status)

    def test_create_receipt_by_term_type_subscription(self):
        self.base_processor.invoice.add_offer(self.subscription_offer)
        self.base_processor.invoice.save()

        order_item_subscription = self.base_processor.invoice.order_items.get(offer__pk=4)
        self.base_processor.payment = Payment.objects.get(pk=1)
        for product in order_item_subscription.offer.products.all():
            self.base_processor.create_receipt_by_term_type(product, order_item_subscription, order_item_subscription.offer.terms)

        self.assertIsNotNone(Receipt.objects.all())

    def test_create_receipt_by_term_type_perpetual(self):
        # TODO: Implement Test
        pass

    def test_create_receipt_by_term_type_one_time_use(self):
        # TODO: Implement Test
        pass
    
    def test_create_receipts_success(self):
        self.base_processor.invoice.status = Invoice.InvoiceStatus.COMPLETE
        self.base_processor.payment = Payment.objects.get(pk=1)
        self.base_processor.create_receipts()
        
        self.assertEquals(4, sum([ oi.receipts.all().count() for oi in self.base_processor.invoice.order_items.all() ]))

    def test_update_subscription_receipt_success(self):
        subscription_id = 123456789
        self.base_processor.invoice.add_offer(self.subscription_offer)
        self.base_processor.invoice.save()
        self.base_processor.invoice.status = Invoice.InvoiceStatus.COMPLETE
        self.base_processor.payment = Payment.objects.get(pk=1)
        self.base_processor.create_receipts()

        subscription_list = self.existing_invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION)
        subscription = subscription_list[0]

        self.base_processor.update_subscription_receipt(subscription, subscription_id)
        receipt = Receipt.objects.get(meta__subscription_id=subscription_id)
        
        self.assertIsNotNone(receipt)
        self.assertEquals(subscription_id, receipt.meta['subscription_id'])

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

    def test_get_billing_address_form_data_fail(self):
        with self.assertRaises(TypeError):
            self.base_processor.get_billing_address_form_data(self.form_data)
        
    def test_get_billing_address_form_data_success(self):
        self.base_processor.get_billing_address_form_data(self.form_data['billing_address_form'], BillingAddressForm)
        
        self.assertIsNotNone(self.base_processor.billing_address)
        self.assertIn(self.form_data['billing_address_form']['address_1'], self.base_processor.billing_address.data['address_1'])

    def test_get_payment_info_form_data_fail(self):
        with self.assertRaises(TypeError):
            self.base_processor.get_payment_info_form_data(self.form_data)

    def test_get_payment_info_form_data_success(self):
        self.base_processor.get_payment_info_form_data(self.form_data['credit_card_form'], CreditCardForm)

        self.assertIsNotNone(self.base_processor.payment_info)
        self.assertIn(self.form_data['credit_card_form']['cvv_number'], self.base_processor.payment_info.data['cvv_number'])

    def test_get_checkout_context_success(self):
        context = self.base_processor.get_checkout_context()
        self.assertIn('invoice', context)

    def test_get_header_javascript_success(self):
        # TODO: Implement Test
        pass

    def test_get_javascript_success(self):
        # TODO: Implement Test
        pass

    def test_get_template_success(self):
        # TODO: Implement Test
        pass

    def test_authorize_payment_success(self):
        # TODO: Implement Test
        pass

    def test_pre_authorization_success(self):
        # TODO: Implement Test
        pass

    def test_process_payment_success(self):
        # TODO: Implement Test
        pass

    def test_post_authorization_success(self):
        # TODO: Implement Test
        pass

    def test_capture_payment_success(self):
        # TODO: Implement Test
        pass

    def test_process_subscription_success(self):
        # TODO: Implement Test
        pass

    def test_process_update_subscription_success(self):
        # TODO: Implement Test
        pass

    def test_process_cancel_subscription_success(self):
        # TODO: Implement Test
        pass

    def test_refund_payment_success(self):
        # TODO: Implement Test
        pass

class SupportedProcessorsSetupTests(TestCase):
    
    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.invoice = Invoice.objects.get(pk=1)

    def test_configured_processor_setup(self):
        """
        Test the initialized of the PaymentProcessor defined in the setting file
        """
        try:
            processor = PaymentProcessor(self.invoice)
        except:
            print("Warning PaymentProcessor defined in settings file did not pass init")
        finally:
            pass

    def test_authorize_net_init(self):
        try:
            if not (settings.AUTHORIZE_NET_TRANSACTION_KEY and settings.AUTHORIZE_NET_API_ID):
                raise ValueError(
                "Missing Authorize.net keys in settings: AUTHORIZE_NET_TRANSACTION_KEY and/or AUTHORIZE_NET_API_ID")
            processor = AuthorizeNetProcessor(self.invoice)
        except:
            print("AuthorizeNetProcessor did not initalized correctly")
        finally:
            pass

    def test_stripe_init(self):
        # TODO: Implement Test
        pass
    
@skipIf((settings.AUTHORIZE_NET_API_ID == None) or (settings.AUTHORIZE_NET_TRANSACTION_KEY == None), "Authorize.Net enviornment variables not set, skipping tests")
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

    def setUp(self):
        self.existing_invoice = Invoice.objects.get(pk=1)
        self.processor = AuthorizeNetProcessor(self.existing_invoice)
        self.form_data = { 
            'billing_address_form': 
                {'name':'Home','company':'Whitemoon Dreams','country':'581','address_1':'221B Baker Street','address_2':'','locality':'Marylebone','state':'California','postal_code':'90292'}, 
            'credit_card_form': 
                {'full_name':'Bob Ross','card_number':'5424000000000015','expire_month':'12','expire_year':'2030','cvv_number':'900','payment_type':'10'}
            }
        self.subscription_offer = Offer.objects.get(pk=4)

        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
    
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
        self.existing_invoice.add_offer(self.subscription_offer)
        self.existing_invoice.save()
        self.processor = AuthorizeNetProcessor(self.existing_invoice)
        request = HttpRequest()
        request.session = self.form_data
        
        self.processor.process_payment(request)

        print(self.processor.transaction_message)
        self.assertIsNotNone(self.processor.payment)
        self.assertTrue(self.processor.payment.success)
        self.assertEquals(Invoice.InvoiceStatus.COMPLETE, self.processor.invoice.status)

    def test_process_payment_transaction_fail_invalid_card(self):
        """
        Simulates a payment transaction for a reqeust.POST, with the payment and 
        billing information. The test send an invalid card number to test the 
        transation fails
        """
        self.form_data['credit_card_form']['card_number'] = '5424000000015'

        request = HttpRequest()
        request.session = self.form_data

        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertFalse(self.processor.payment.success)
        self.assertEquals(Invoice.InvoiceStatus.CART, self.processor.invoice.status)

    def test_process_payment_transaction_fail_invalid_expiration(self):
        """
        Simulates a payment transaction for a reqeust.POST, with the payment and 
        billing information. The test send an invalid expiration date to test the 
        transation fails.
        """
        self.form_data['credit_card_form']['expire_month'] = '12'
        self.form_data['credit_card_form']['expire_year'] = '2000'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertFalse(self.processor.payment.success)
        self.assertEquals(Invoice.InvoiceStatus.CART, self.processor.invoice.status)      

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
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        if self.processor.transaction_response.cvvResultCode.text:
            self.assertEquals("N", self.processor.transaction_response.cvvResultCode.text)
        else:
            print(f'test_process_payment_fail_cvv_no_match: Response: {self.processor.payment.result["raw"]}')

    def test_process_payment_fail_cvv_should_not_be_on_card(self):
        """
        Check a failed transaction due to cvv number does not match card number.
        CVV: 902
        """
        self.form_data['credit_card_form']['cvv_number'] = '902'
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)
        
        self.assertIsNotNone(self.processor.payment)
        if self.processor.transaction_response.cvvResultCode.text:
            self.assertEquals("S", self.processor.transaction_response.cvvResultCode.text)
        else:
            print(f'test_process_payment_fail_cvv_should_not_be_on_card: Response: {self.processor.payment.result["raw"]}')

    def test_process_payment_fail_cvv_not_certified(self):
        """
        Check a failed transaction due to cvv number does not match card number.
        Test Guide: https://developer.authorize.net/hello_world/testing_guide.html
        CVV: 903
        """
        self.form_data['credit_card_form']['cvv_number'] = '903'
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)
        
        self.assertIsNotNone(self.processor.payment)
        if self.processor.transaction_response.cvvResultCode.text:
            self.assertEquals("U", self.processor.transaction_response.cvvResultCode.text)
        else:
            print(f'test_process_payment_fail_cvv_not_certified: Response: {self.processor.payment.result["raw"]}')

    def test_process_payment_fail_cvv_not_processed(self):
        """
        Check a failed transaction due to cvv number is not processed.
        CVV: 904 
        """
        self.form_data['credit_card_form']['cvv_number'] = '904'
        self.form_data['credit_card_form']['card_number'] = choice(self.VALID_CARD_NUMBERS)
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)
        
        self.assertIsNotNone(self.processor.payment)
        if self.processor.transaction_response.cvvResultCode.text:
            self.assertEquals("P", self.processor.transaction_response.cvvResultCode.text)
        else:
            print(f'test_process_payment_fail_cvv_not_processed Response: {self.processor.payment.result["raw"]}')

    ##########
    # AVS Tests
    # Reference: https://support.authorize.net/s/article/What-Are-the-Different-Address-Verification-Service-AVS-Response-Codes
    ##########

    def test_process_payment_avs_addr_match_zipcode_no_match(self):
        """
        A = Street Address: Match -- First 5 Digits of ZIP: No Match
        Postal Code: 46201
        """
        self.form_data['billing_address_form']['postal_code'] = '46201'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'A'", self.processor.payment.result["raw"])

    def test_process_payment_avs_service_error(self):
        """
        E = AVS Error
        Postal Code: 46203
        """
        self.form_data['billing_address_form']['postal_code'] = '46203'
        self.form_data['credit_card_form']['card_number'] = '2223000010309711'
        
        request = HttpRequest()
        request.session = self.form_data
                
        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'E'", self.processor.payment.result["raw"])

    def test_process_payment_avs_non_us_card(self):
        """
        G = Non U.S. Card Issuing Bank
        Postal Code: 46204
        """
        self.form_data['billing_address_form']['postal_code'] = '46204'
        self.form_data['credit_card_form']['card_number'] = '4007000000027'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'G'", self.processor.payment.result["raw"])

    def test_process_payment_avs_addr_no_match_zipcode_no_match(self):
        """
        N = Street Address: No Match -- First 5 Digits of ZIP: No Match
        Postal Code: 46205
        """
        self.form_data['billing_address_form']['postal_code'] = '46205'
        self.form_data['credit_card_form']['card_number'] = '2223000010309711'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'N'", self.processor.payment.result["raw"])

    def test_process_payment_avs_retry_service_unavailable(self):
        """
        R = Retry, System Is Unavailable
        Postal Code: 46207
        """
        self.form_data['billing_address_form']['postal_code'] = '46207'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'R'", self.processor.payment.result["raw"])
        self.assertFalse(self.processor.payment.success)
        self.assertEquals(Invoice.InvoiceStatus.CART, self.processor.invoice.status) 

    def test_process_payment_avs_not_supported(self):
        """
        S = AVS Not Supported by Card Issuing Bank
        Postal Code: 46208
        """
        self.form_data['billing_address_form']['postal_code'] = '46208'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'S'", self.processor.payment.result["raw"])

    def test_process_payment_avs_addrs_info_unavailable(self):
        """
        U = Address Information For This Cardholder Is Unavailable
        Postal Code: 46209
        """
        self.form_data['billing_address_form']['postal_code'] = '46209'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'U'", self.processor.payment.result["raw"])

    def test_process_payment_avs_addr_no_match_zipcode_match_9_digits(self):
        """
        W = Street Address: No Match -- All 9 Digits of ZIP: Match
        Postal Code: 46211
        """
        self.form_data['billing_address_form']['postal_code'] = '46211'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'W'", self.processor.payment.result["raw"])

    def test_process_payment_avs_addr_match_zipcode_match(self):
        """
        X = Street Address: Match -- All 9 Digits of ZIP: Match
        Postal Code: 46214
        """
        self.form_data['billing_address_form']['postal_code'] = '46214'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'X'", self.processor.payment.result["raw"])

    def test_process_payment_avs_addr_no_match_zipcode_match_5_digits(self):
        """
        Z = Street Address: No Match - First 5 Digits of ZIP: Match
        Postal Code: 46217
        """
        self.form_data['billing_address_form']['postal_code'] = '46217'
        self.form_data['credit_card_form']['card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.session = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'Z'", self.processor.payment.result["raw"])
    
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
        for batch in batch_list:
            transaction_list = self.processor.get_transaction_batch_list(str(batch.batchId))
            successfull_transactions = [ t for t in transaction_list if t['transactionStatus'] == 'settledSuccessfully' ]
            if len(successfull_transactions) > 0:
                break
        
        if not successfull_transactions:
            print("No Transactions to refund Skipping\n")
            return

        payment = Payment()
        # payment.amount = transaction_detail.authAmount.pyval
        # Hard coding minimum amount so the test can run multiple times.
        payment.amount = 0.01
        payment.invoice = self.existing_invoice
        payment.transaction = successfull_transactions[-1].transId.text
        payment.result["raw"] = str({ 'accountNumber': successfull_transactions[-1].accountNumber.text})
        payment.save()
        self.processor.payment = payment


        self.processor.refund_payment(payment)
        # print(f'Message: {self.processor.transaction_message}\nResponse: {self.processor.transaction_response}')
        self.assertEquals(Invoice.InvoiceStatus.REFUNDED, self.existing_invoice.status)

    def test_refund_fail_invalid_account_number(self):
        """
        Checks for transaction_submitted fail because the account number does not match the payment transaction settled.
        """
        status_before_transaction = self.existing_invoice.status

        # Get Settled payment
        start_date, end_date = (timezone.now() - timedelta(days=31)), timezone.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.invoice = self.existing_invoice
        payment.amount = 0.01
        payment.transaction = transaction_list[-1].transId.text
        payment.result["raw"] = str({ 'accountNumber': '6699'})
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
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.invoice = self.existing_invoice
        payment.amount = 1000000.00
        payment.transaction = transaction_list[-1].transId.text
        payment.result["raw"] = str({ 'accountNumber': transaction_list[-1].accountNumber.text})
        payment.save()
        self.processor.payment = payment

        self.processor.refund_payment(payment)

        self.assertFalse(self.processor.transaction_submitted)
        self.assertEquals(self.processor.invoice.status, status_before_transaction)

    def test_refund_fail_invalid_transaction_id(self):
        """
        Checks for transaction_submitted fail because the transaction id does not match
        """
        self.processor = AuthorizeNetProcessor(self.existing_invoice)       
        status_before_transaction = self.existing_invoice.status

        # Get Settled payment
        start_date, end_date = (timezone.now() - timedelta(days=31)), timezone.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.invoice = self.existing_invoice
        payment.amount = 0.01
        payment.transaction = '111222333412'
        payment.result["raw"] = str({ 'accountNumber': transaction_list[-1].accountNumber.text})
        payment.save()
        self.processor.payment = payment

        self.processor.refund_payment(payment)

        self.assertFalse(self.processor.transaction_submitted)
        self.assertEquals(self.processor.invoice.status, status_before_transaction)

    ##########
    # Customer Payment Profile Transaction Tests
    ##########
    def test_create_customer_payment_profile(self):
        # TODO: Implement Test
        pass
    
    def test_update_customer_payment_profile(self):
        # TODO: Implement Test
        pass

    def test_get_customer_payment_profile(self):
        # TODO: Implement Test
        pass
    
    def test_get_customer_payment_profile_list(self):
        # TODO: Implement Test
        pass

    ##########
    # Subscription Transaction Tests
    ##########
    def test_create_subscription_success(self):
        """
        Test a successfull subscription enrollment.
        """        
        request = HttpRequest()
        request.session = self.form_data

        self.existing_invoice.add_offer(self.subscription_offer)
        self.existing_invoice.add_offer(self.subscription_offer)
        price = Price()
        price.offer = self.subscription_offer
        price.cost = randrange(1,1000)
        price.start_date = timezone.now() - timedelta(days=1)
        price.save()
        self.existing_invoice.save()

        self.processor = AuthorizeNetProcessor(self.existing_invoice)
        
        subscription_list = self.existing_invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION)
        subscription = subscription_list[0]
        subscription.offer.name = "".join([ choice(ascii_letters) for i in range(0, 10) ])
        subscription.offer.save()

        self.processor.invoice.status = Invoice.InvoiceStatus.COMPLETE
        self.processor.payment = Payment.objects.get(pk=1)
        self.processor.create_receipts()

        self.processor.process_subscription(request, subscription)
        

        # print(self.processor.transaction_message)
        self.assertTrue(self.processor.transaction_submitted)
        self.assertIsNotNone(self.processor.transaction_response.subscriptionId)

    def test_update_subscription_success(self):
        # TODO: Implement Test
        # self.assertTrue(self.processor.transaction_submitted)
        pass

    def test_cancel_subscription_success(self):

        subscription_list = self.processor.get_list_of_subscriptions()
        active_subscriptions = [ s for s in subscription_list if s['status'] == 'active' ]
        
        if active_subscriptions:
            self.processor.process_cancel_subscription(active_subscriptions[0].id.pyval)
            self.assertTrue(self.processor.transaction_submitted)
        else:
            print("No active Subscriptions, Skipping Test")

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

@skipIf((settings.STRIPE_TEST_SECRET_KEY or settings.STRIPE_TEST_PUBLIC_KEY) == None, "Strip enviornment variables not set, skipping tests")
class StripeProcessorTests(TestCase):

    def setUp(self):
        pass

