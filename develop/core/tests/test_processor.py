from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.sites.models import Site
from django.http import HttpRequest, QueryDict
from django.test import TestCase, Client
from django.urls import reverse
from unittest import skipIf
from core.models import Product
from vendor.models import Invoice
from vendor.models.address import Country
from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.processors import PaymentProcessor


###############################
# Test constants
###############################

PAYMENT = {
    "payment": {
        "creditCard": {
            "cardNumber": "5424000000000015",
            "expirationDate": "2020-12",
            "cardCode": "999"
        }
    }
}

TEST_PAYLOAD = {
    "createTransactionRequest": {
        "merchantAuthentication": {
            "name": "79MvGs6X3P",
            "transactionKey": "4tbEK65FB8Tht59Y"
        },
        "refId": "123455",
        "transactionRequest": {
            "transactionType": "authCaptureTransaction",
            "amount": "5",
            "payment": {
                "creditCard": {
                    "cardNumber": "5424000000000015",
                    "expirationDate": "2020-12",
                    "cardCode": "999"
                }
            },
            "lineItems": {
                "lineItem": {
                    "itemId": "1",
                    "name": "vase",
                    "description": "Cannes logo",
                    "quantity": "18",
                    "unitPrice": "45.00"
                }
            },
            "tax": {
                "amount": "4.26",
                "name": "level2 tax name",
                "description": "level2 tax"
            },
            "duty": {
                "amount": "8.55",
                "name": "duty name",
                "description": "duty description"
            },
            "shipping": {
                "amount": "4.26",
                "name": "level2 tax name",
                "description": "level2 tax"
            },
            "poNumber": "456654",
            "customer": {
                "id": "99999456654"
            },
            "billTo": {
                "firstName": "Ellen",
                "lastName": "Johnson",
                "company": "Souveniropolis",
                "address": "14 Main Street",
                "city": "Pecan Springs",
                "state": "TX",
                "zip": "44628",
                "country": "USA"
            },
            "shipTo": {
                "firstName": "China",
                "lastName": "Bayles",
                "company": "Thyme for Tea",
                "address": "12 Main Street",
                "city": "Pecan Springs",
                "state": "TX",
                "zip": "44628",
                "country": "USA"
            },
            "customerIP": "192.168.1.1",
            "transactionSettings": {
                "setting": {
                    "settingName": "testRequest",
                    "settingValue": "false"
                }
            },
            "userFields": {
                "userField": [
                    {
                        "name": "MerchantDefinedFieldName1",
                        "value": "MerchantDefinedFieldValue1"
                    },
                    {
                        "name": "favorite_color",
                        "value": "blue"
                    }
                ]
            }
        }
    }
}
@skipIf((settings.AUTHORIZE_NET_API_ID or settings.AUTHORIZE_NET_TRANSACTION_KEY) == None, "Authorize.Net enviornment variables not set, skipping tests")
class AuthorizeNetProcessorTests(TestCase):
    fixtures = ['site', 'user', 'product', 'price', 'offer', 'order_item', 'invoice']

    def setUp(self):
        self.existing_invoice = Invoice.objects.get(pk=1)

    def test_environment_variables_set(self):
        self.assertIsNotNone(settings.AUTHORIZE_NET_TRANSACTION_KEY)
        self.assertIsNotNone(settings.AUTHORIZE_NET_API_ID)

    def test_processor_initialization_success(self):
        processor = PaymentProcessor(self.existing_invoice)

        self.assertEquals(processor.provider, 'AuthorizeNetProcessor')
        self.assertIsNotNone(processor.invoice)
        self.assertIsNotNone(processor.merchant_auth)
        self.assertIsNotNone(processor.merchant_auth.transactionKey)
        self.assertIsNotNone(processor.merchant_auth.name)
    
    def test_get_checkout_context(self):
        context = {}
        payment_processor = PaymentProcessor(invoice=self.existing_invoice) 
        context = payment_processor.get_checkout_context()
        
        self.assertIn('invoice', context)
        self.assertIn('credit_card_form', context)
        self.assertIn('billing_address_form', context)
    
    def test_process_payment_transaction_success(self):
        """
        By passing in the invoice, setting the payment info and billing 
        address, process the payment and make sure it succeeds.
        """
        request = HttpRequest()
        request.POST = QueryDict('billing-address-name=Home&billing-address-company=Whitemoon Dreams&billing-address-country=581&billing-address-address_1=221B Baker Street&billing-address-address_2=&billing-address-locality=Marylebone&billing-address-state=California&billing-address-postal_code=90292&credit-card-full_name=Bob Ross&credit-card-card_number=5424000000000015&credit-card-expire_month=12&credit-card-expire_year=2030&credit-card-cvv_number=999')

        processor = PaymentProcessor(self.existing_invoice)
        processor.process_payment(request)

        self.assertIsNotNone(Payment.objects.get(invoice=self.existing_invoice))

    def test_auth_capture_transaction_fail(self):
        # TODO: Implement Test.
        # payment_processor = PaymentProcessor(self.existing_invoice)
        # payment_processor.set_payment_info(card_number='5424000000000015', expire_month='12', expire_year='2020', cvv_number='999')
        # payment_processor.authorize_payment()
        pass

    def test_refund_success(self):
        processor = PaymentProcessor(self.existing_invoice)
        processor.refund_payment(

    def test_refund_fail(self):
        # TODO: Implement Test
        pass

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

    def test_create_subscription(self):
        # TODO: Implement Test
        pass

    def test_update_subscription(self):
        # TODO: Implement Test
        pass

    def test_cancel_subscription(self):
        # TODO: Implement Test
        pass

    def test_create_subscription_customer_profile(self):
        # TODO: Implement Test
        pass
    
    

@skipIf(settings.AUTHORIZE_NET_API_ID and settings.AUTHORIZE_NET_TRANSACTION_KEY, "Strip enviornment variables not set, skipping tests")
class StripeProcessorTests(TestCase):

    def setUp(self):
        pass