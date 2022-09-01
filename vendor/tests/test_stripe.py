import stripe

from django.test import TestCase, Client, tag
from vendor.processors.stripe_objects import *
from vendor.processors import StripeProcessor

# @skipIf((settings.STRIPE_TEST_SECRET_KEY or settings.STRIPE_TEST_PUBLIC_KEY) is None, "Strip enviornment variables not set, skipping tests")
# class StripeProcessorTests(TestCase):

#     fixtures = ['user', 'unit_test']

#     def setUp(self):
#         TEST_ACK = "acct_1LbUg3R6Vaz8QGf8"
#         stripe.api_key = "sk_test_51LYCNjJHHVfmV6EHPwkh9bogbRyTQFoiGV85yUrQyPFyur3BI2Rjtkhi7XCCNIsPvzOlYTVjzOYmljHPe1X2caIr00uVSfVkmn"

#     def test_stripe_connect(self):
#         test_connect = stripe.Account.create(country="US", type="custom", capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}})
        

class StripeCRUDObjectTests(TestCase):

    def init_test_objects(self):
        self.valid_metadata = {'site': ['sc.online.edu', 'jikei.tc.com']}
        self.valid_addr = {'city': "na",'country': "US",'line1': "Salvatierra walk",'postal_code': "90321",'state': 'CA'}
        
        self.cus_norrin_radd = {'name': 'Norrin Radd', 'email': 'norrin@radd.com', 'metadata': self.valid_metadata}
        
        self.pro_monthly_license = {'name': "Monthly License", 'metadata': self.valid_metadata}
        self.pro_annual_license = {"name": "Annual Subscription", 'metadata': self.valid_metadata}

        self.pri_monthly = {"currency": "usd", "unit_amount": 1024, "recurring": {"interval": "month", "interval_count": 1, "usage_type": "licensed"}, 'metadata': self.valid_metadata}

    def setUp(self):
        stripe.api_key = "sk_test_51LYCNjJHHVfmV6EHPwkh9bogbRyTQFoiGV85yUrQyPFyur3BI2Rjtkhi7XCCNIsPvzOlYTVjzOYmljHPe1X2caIr00uVSfVkmn"
        self.init_test_objects()

    def test_create_customer_no_metadata_fail(self):
        del(self.cus_norrin_radd['metadata'])

        with self.assertRaises(TypeError):
            crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)

    def test_create_customer_success(self):
        stripe_customer = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)
        
        self.assertIsNotNone(stripe_customer.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.CUSTOMER, stripe_customer.id)

    def test_create_customer_with_address_success(self):
        self.cus_norrin_radd['address'] = self.valid_addr

        stripe_customer = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)
        
        self.assertIsNotNone(stripe_customer.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.CUSTOMER, stripe_customer.id)

    def test_create_product_success(self):
        stripe_product = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **self.pro_annual_license)

        self.assertIsNotNone(stripe_product.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.PRODUCT, stripe_product.id)

    def test_create_product_no_name_fail(self):
        del(self.pro_monthly_license['name'])

        with self.assertRaises(stripe.error.StripeError):
            crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **self.pro_monthly_license)

    def test_create_price_product_data_success(self):
        del(self.pro_monthly_license['metadata'])
        self.pri_monthly['product_data'] = self.pro_monthly_license

        stripe_price = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRICE, **self.pri_monthly)

        self.assertIsNotNone(stripe_price.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.PRICE, stripe_price.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.PRODUCT, stripe_price.product)

    def test_create_price_product_id_success(self):
        stripe_product = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **self.pro_annual_license)
        self.pri_monthly['product'] = stripe_product.id

        stripe_price = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRICE, **self.pri_monthly)

        self.assertIsNotNone(stripe_price.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.PRICE, stripe_price.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.PRODUCT, stripe_product.id)

    def test_create_price_invalid_field_fail(self):
        self.pri_monthly['type'] = "This is not a valid field"

        with self.assertRaises(stripe.error.InvalidRequestError):
            crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRICE, **self.pri_monthly)
