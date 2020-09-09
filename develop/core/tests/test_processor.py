from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.sites.models import Site
from django.http import HttpRequest, QueryDict
from django.test import TestCase, Client
from django.urls import reverse
from core.models import Product
from random import randrange, choice
from vendor.models import Invoice, Payment, Offer, Price
from vendor.models.address import Country
from vendor.models.choice import TermType
from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.processors.authorizenet import AuthorizeNetProcessor
from unittest import skipIf

from string import ascii_letters

###############################
# Test constants
###############################

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
        self.form_data = QueryDict('billing-address-name=Home&billing-address-company=Whitemoon Dreams&billing-address-country=581&billing-address-address_1=221B Baker Street&billing-address-address_2=&billing-address-locality=Marylebone&billing-address-state=California&billing-address-postal_code=90292&credit-card-full_name=Bob Ross&credit-card-card_number=5424000000000015&credit-card-expire_month=12&credit-card-expire_year=2030&credit-card-cvv_number=900&credit-card-payment_type=10', mutable=True)
        

    
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
        self.existing_invoice.add_offer(Offer.objects.get(pk=4))
        self.existing_invoice.save()
        self.processor = AuthorizeNetProcessor(self.existing_invoice)
        request = HttpRequest()
        request.POST = self.form_data
        
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
        self.form_data['credit-card-card_number'] = '5424000000015'

        request = HttpRequest()
        request.POST = self.form_data

        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertFalse(self.processor.payment.success)
        self.assertEquals(Invoice.InvoiceStatus.FAILED, self.processor.invoice.status)

    def test_process_payment_transaction_fail_invalid_expiration(self):
        """
        Simulates a payment transaction for a reqeust.POST, with the payment and 
        billing information. The test send an invalid expiration date to test the 
        transation fails.
        """
        self.form_data['credit-card-expire_month'] = '12'
        self.form_data['credit-card-expire_year'] = '2000'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertFalse(self.processor.payment.success)
        self.assertEquals(Invoice.InvoiceStatus.FAILED, self.processor.invoice.status)      

    ##########
    # CVV Tests
    # Reference: Test Guide: https://developer.authorize.net/hello_world/testing_guide.html
    ##########
    def test_process_payment_fail_cvv_no_match(self):
        """
        Check a failed transaction due to cvv number does not match card number.
        CVV: 901 
        """
        self.form_data['credit-card-cvv_number'] = '901'
        self.form_data['credit-card-card_number'] = choice(self.VALID_CARD_NUMBERS)
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        if self.processor.transaction_response.cvvResultCode.text:
            self.assertEquals("N", self.processor.transaction_response.cvvResultCode.text)
        else:
            print(f'test_process_payment_fail_cvv_no_match: Response: {self.payment.result}')

    def test_process_payment_fail_cvv_should_not_be_on_card(self):
        """
        Check a failed transaction due to cvv number does not match card number.
        CVV: 902
        """
        self.form_data['credit-card-cvv_number'] = '902'
        self.form_data['credit-card-card_number'] = choice(self.VALID_CARD_NUMBERS)
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)
        
        self.assertIsNotNone(self.processor.payment)
        if self.processor.transaction_response.cvvResultCode.text:
            self.assertEquals("S", self.processor.transaction_response.cvvResultCode.text)
        else:
            print(f'test_process_payment_fail_cvv_should_not_be_on_card: Response: {self.payment.result}')

    def test_process_payment_fail_cvv_not_certified(self):
        """
        Check a failed transaction due to cvv number does not match card number.
        Test Guide: https://developer.authorize.net/hello_world/testing_guide.html
        CVV: 903
        """
        self.form_data['credit-card-cvv_number'] = '903'
        self.form_data['credit-card-card_number'] = choice(self.VALID_CARD_NUMBERS)
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)
        
        self.assertIsNotNone(self.processor.payment)
        if self.processor.transaction_response.cvvResultCode.text:
            self.assertEquals("U", self.processor.transaction_response.cvvResultCode.text)
        else:
            print(f'test_process_payment_fail_cvv_not_certified: Response: {self.payment.result}')


    def test_process_payment_fail_cvv_not_processed(self):
        """
        Check a failed transaction due to cvv number is not processed.
        CVV: 904 
        """
        self.form_data['credit-card-cvv_number'] = '904'
        self.form_data['credit-card-card_number'] = choice(self.VALID_CARD_NUMBERS)
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)
        
        self.assertIsNotNone(self.processor.payment)
        if self.processor.transaction_response.cvvResultCode.text:
            self.assertEquals("P", self.processor.transaction_response.cvvResultCode.text)
        else:
            print(f'test_process_payment_fail_cvv_not_processed Response: {self.payment.result}')

    
    ##########
    # AVS Tests
    # Reference: https://support.authorize.net/s/article/What-Are-the-Different-Address-Verification-Service-AVS-Response-Codes
    ##########

    def test_process_payment_avs_addr_match_zipcode_no_match(self):
        """
        A = Street Address: Match -- First 5 Digits of ZIP: No Match
        Postal Code: 46201
        """
        self.form_data['billing-address-postal_code'] = '46201'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'A'", self.processor.payment.result)

    def test_process_payment_avs_service_error(self):
        """
        E = AVS Error
        Postal Code: 46203
        """
        self.form_data['billing-address-postal_code'] = '46203'
        self.form_data['credit-card-card_number'] = '2223000010309711'
        
        request = HttpRequest()
        request.POST = self.form_data
                
        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'E'", self.processor.payment.result)

    def test_process_payment_avs_non_us_card(self):
        """
        G = Non U.S. Card Issuing Bank
        Postal Code: 46204
        """
        self.form_data['billing-address-postal_code'] = '46204'
        self.form_data['credit-card-card_number'] = '4007000000027'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'G'", self.processor.payment.result)

    def test_process_payment_avs_addr_no_match_zipcode_no_match(self):
        """
        N = Street Address: No Match -- First 5 Digits of ZIP: No Match
        Postal Code: 46205
        """
        self.form_data['billing-address-postal_code'] = '46205'
        self.form_data['credit-card-card_number'] = '2223000010309711'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'N'", self.processor.payment.result)

    def test_process_payment_avs_retry_service_unavailable(self):
        """
        R = Retry, System Is Unavailable
        Postal Code: 46207
        """
        self.form_data['billing-address-postal_code'] = '46207'
        self.form_data['credit-card-card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'R'", self.processor.payment.result)
        self.assertFalse(self.processor.payment.success)
        self.assertEquals(Invoice.InvoiceStatus.FAILED, self.processor.invoice.status) 

    def test_process_payment_avs_not_supported(self):
        """
        S = AVS Not Supported by Card Issuing Bank
        Postal Code: 46208
        """
        self.form_data['billing-address-postal_code'] = '46208'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'S'", self.processor.payment.result)

    def test_process_payment_avs_addrs_info_unavailable(self):
        """
        U = Address Information For This Cardholder Is Unavailable
        Postal Code: 46209
        """
        self.form_data['billing-address-postal_code'] = '46209'
        self.form_data['credit-card-card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'U'", self.processor.payment.result)

    def test_process_payment_avs_addr_no_match_zipcode_match_9_digits(self):
        """
        W = Street Address: No Match -- All 9 Digits of ZIP: Match
        Postal Code: 46211
        """
        self.form_data['billing-address-postal_code'] = '46211'
        self.form_data['credit-card-card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'W'", self.processor.payment.result)

    def test_process_payment_avs_addr_match_zipcode_match(self):
        """
        X = Street Address: Match -- All 9 Digits of ZIP: Match
        Postal Code: 46214
        """
        self.form_data['billing-address-postal_code'] = '46214'
        self.form_data['credit-card-card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'X'", self.processor.payment.result)

    def test_process_payment_avs_addr_no_match_zipcode_match_5_digits(self):
        """
        Z = Street Address: No Match - First 5 Digits of ZIP: Match
        Postal Code: 46217
        """
        self.form_data['billing-address-postal_code'] = '46217'
        self.form_data['credit-card-card_number'] = '5424000000000015'
        
        request = HttpRequest()
        request.POST = self.form_data

        self.processor.invoice.total = randrange(1,1000)
        self.processor.process_payment(request)

        self.assertIsNotNone(self.processor.payment)
        self.assertIn("'avsResultCode': 'Z'", self.processor.payment.result)
    
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
        start_date, end_date = (datetime.now() - timedelta(days=31)), datetime.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))
        successfull_transactions = [ t for t in transaction_list if t['transactionStatus'] == 'settledSuccessfully' ]

        payment = Payment()
        # payment.amount = transaction_detail.authAmount.pyval
        # Hard coding minimum amount so the test can run multiple times.
        payment.amount = 0.01
        payment.transaction = successfull_transactions[-1].transId.text
        payment.result = str({ 'accountNumber': successfull_transactions[-1].accountNumber.text})

        self.processor.refund_payment(payment)
        print(f'Message: {self.processor.transaction_message}\nResponse: {self.processor.transaction_response}')
        self.assertEquals(Invoice.InvoiceStatus.REFUNDED, self.existing_invoice.status)

    def test_refund_fail_invalid_account_number(self):
        """
        Checks for transaction_submitted fail because the account number does not match the payment transaction settled.
        """
        status_before_transaction = self.existing_invoice.status

        # Get Settled payment
        start_date, end_date = (datetime.now() - timedelta(days=31)), datetime.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.amount = 0.01
        payment.transaction = transaction_list[-1].transId.text
        payment.result = str({ 'accountNumber': '6699'})

        self.processor.refund_payment(payment)

        self.assertFalse(self.processor.transaction_submitted)
        self.assertEquals(self.processor.invoice.status, status_before_transaction)

    def test_refund_fail_invalid_amount(self):
        """
        Checks for transaction_submitted fail because the amount exceeds the payment transaction settled.
        """
        status_before_transaction = self.existing_invoice.status

        # Get Settled payment
        start_date, end_date = (datetime.now() - timedelta(days=31)), datetime.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.amount = 1000000.00
        payment.transaction = transaction_list[-1].transId.text
        payment.result = str({ 'accountNumber': transaction_list[-1].accountNumber.text})

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
        start_date, end_date = (datetime.now() - timedelta(days=31)), datetime.now()
        batch_list = self.processor.get_settled_batch_list(start_date, end_date)
        transaction_list = self.processor.get_transaction_batch_list(str(batch_list[-1].batchId))

        payment = Payment()
        payment.amount = 0.01
        payment.transaction = '111222333412'
        payment.result = str({ 'accountNumber': transaction_list[-1].accountNumber.text})

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
        request.POST = self.form_data

        self.existing_invoice.add_offer(Offer.objects.get(pk=4))
        self.existing_invoice.add_offer(Offer.objects.get(pk=4))
        price = Price()
        price.offer = Offer.objects.get(pk=4)
        price.cost = randrange(1,1000)
        price.start_date = datetime.now() - timedelta(days=1)
        price.save()
        self.existing_invoice.save()

        self.processor = AuthorizeNetProcessor(self.existing_invoice)
        
        subscription_list = self.existing_invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION)
        subscription = subscription_list[0]
        subscription.offer.name = "".join([ choice(ascii_letters) for i in range(0, 10) ])
        self.processor.process_subscription(request, subscription)
        

        print(self.processor.transaction_message)
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
            self.processor.process_cancel_subscription(active_subscriptions[0])
            self.assertTrue(self.processor.transaction_submitted)
        else:
            print("No active Subscriptions, Skipping Test")
            pass

@skipIf((settings.STRIPE_TEST_SECRET_KEY or settings.STRIPE_TEST_PUBLIC_KEY) == None, "Strip enviornment variables not set, skipping tests")
class StripeProcessorTests(TestCase):

    def setUp(self):
        pass

