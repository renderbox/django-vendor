from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Product
from vendor.models import Offer, Price, OrderItem


import requests
import json
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

URL_AUTHORIZE_NET = 'https://apitest.authorize.net/xml/v1/request.api'

class AuthorizeNetProcessorTests(TestCase):

    def setUp(self):
        pass

    def test_get_checkout_context(self):
        # TODO: Implement Test
        pass
    
    def test_auth_capture_transaction_success(self):
        r = requests.post(URL_AUTHORIZE_NET, json=TEST_PAYLOAD)
        print(r)
        pass

    def test_auth_capture_transaction_fail(self):
        # TODO: Implement Test
        pass

    def test_refund_success(self):
        # TODO: Implement Test
        pass

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
    
    

class StripeProcessorTests(TestCase):

    def setUp(self):
        pass