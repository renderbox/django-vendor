import stripe

from django.conf import settings
from django.test import TestCase, Client, tag

from vendor.processors.stripe_objects import *
from vendor.processors import StripeProcessor

@skipIf((settings.STRIPE_PUBLIC_KEY or settings.STRIPE_SECRET_KEY) is None, "Strip enviornment variables not set, skipping tests")
class StripeProcessorTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        TEST_ACK = "acct_1LbUg3R6Vaz8QGf8"
        stripe.api_key = "sk_test_51LYCNjJHHVfmV6EHPwkh9bogbRyTQFoiGV85yUrQyPFyur3BI2Rjtkhi7XCCNIsPvzOlYTVjzOYmljHPe1X2caIr00uVSfVkmn"

    def test_stripe_connect(self):
        test_connect = stripe.Account.create(country="US", type="custom", capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}})
        

@skipIf((settings.STRIPE_PUBLIC_KEY or settings.STRIPE_SECRET_KEY) is None, "Strip enviornment variables not set, skipping tests")
class StripeCRUDObjectTests(TestCase):

    def init_test_objects(self):
        self.valid_metadata = {'site': 'sc.online.edu'}
        self.valid_addr = {'city': "na",'country': "US",'line1': "Salvatierra walk",'postal_code': "90321",'state': 'CA'}
        
        self.cus_norrin_radd = {'name': 'Norrin Radd', 'email': 'norrin@radd.com', 'metadata': self.valid_metadata}
        
        self.pro_monthly_license = {'name': "Monthly License", 'metadata': self.valid_metadata}
        self.pro_annual_license = {"name": "Annual Subscription", 'metadata': self.valid_metadata}

        self.pri_monthly = {"currency": "usd", "unit_amount": 1024, "recurring": {"interval": "month", "interval_count": 1, "usage_type": "licensed"}, 'metadata': self.valid_metadata}
        self.card = {'number': 4242424242424242, 'exp_month': "10", 'exp_year': "2023", 'cvc': "9000"}
        self.payment_method = {'type': 'card', 'card': self.card}
        self.cou_first_three_months_coupon = {
            "currency": "usd",
            "duration": "repeating",
            "duration_in_months": 3,
            "name": "25.5% off",
            "percent_off": 25.5,
            'metadata': self.valid_metadata
            }
        self.cou_first_month_free = {
            "currency": "usd",
            "duration": "once",
            "name": "100% off",
            "percent_off": 100,
            'metadata': self.valid_metadata
            }

    def setUp(self):
        stripe.api_key = settings.STRIPE_PUBLIC_KEY
        self.init_test_objects()

    def test_create_customer_no_metadata_fail(self):
        del(self.cus_norrin_radd['metadata'])

        with self.assertRaises(TypeError):
            crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)

    ##########
    # Customer CRUD
    def test_create_customer_success(self):
        stripe_customer = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)
        
        self.assertIsNotNone(stripe_customer.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.CUSTOMER, stripe_customer.id)

    def test_create_customer_with_address_success(self):
        self.cus_norrin_radd['address'] = self.valid_addr

        stripe_customer = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)
        
        self.assertIsNotNone(stripe_customer.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.CUSTOMER, stripe_customer.id)

    ##########
    # Product CRUD
    def test_create_product_success(self):
        stripe_product = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **self.pro_annual_license)

        self.assertIsNotNone(stripe_product.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.PRODUCT, stripe_product.id)

    def test_create_product_no_name_fail(self):
        del(self.pro_monthly_license['name'])

        with self.assertRaises(stripe.error.StripeError):
            crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **self.pro_monthly_license)

    ##########
    # Price CRUD
    def test_create_price_product_data_success(self):
        del(self.pro_monthly_license['metadata'])
        self.pri_monthly['product_data'] = self.pro_monthly_license

        stripe_price = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRICE, **self.pri_monthly)

        self.assertIsNotNone(stripe_price.id)

    def test_create_price_product_id_success(self):
        stripe_product = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **self.pro_annual_license)
        self.pri_monthly['product'] = stripe_product.id

        stripe_price = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRICE, **self.pri_monthly)

        self.assertIsNotNone(stripe_price.id)

    def test_create_price_invalid_field_fail(self):
        self.pri_monthly['type'] = "This is not a valid field"

        with self.assertRaises(stripe.error.InvalidRequestError):
            crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRICE, **self.pri_monthly)

    ##########
    # Coupon CRUD
    def test_create_coupon_success(self):
        stripe_coupon = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.COUPON, **self.cou_first_month_free)

        self.assertIsNotNone(stripe_coupon.id)
        crud_stripe_object(CRUDChoices.DELETE, StripeObjects.COUPON, stripe_coupon.id)

    ##########
    # Subscription CRUD
    def test_create_subscription_success(self):
        stripe_cus_norrin_radd = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)
        
        stripe_payment_method = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PAYMENT_METHOD, **self.payment_method)
        setup_intent_object = {
            'customer': stripe_cus_norrin_radd.id,
            'confirm': True,
            'payment_method_types': ['card'],
            'payment_method': stripe_payment_method.id,
            'metadata': self.valid_metadata
        }
        stripe_setup_intent = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.SETUP_INTENT, **setup_intent_object)
        
        
        stripe_pro_monthly = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **self.pro_monthly_license)
        self.pri_monthly['product'] = stripe_pro_monthly.id
        stripe_price = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRICE, **self.pri_monthly)
        
        subscription_obj = {
            'customer': stripe_cus_norrin_radd.id,
            'items': [{'price': stripe_price.id}],
            'default_payment_method': stripe_payment_method.id,
            'metadata': self.valid_metadata,

        }
        stripe_sub = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.SUBSCRIPTION, **subscription_obj)

        self.assertIsNotNone(stripe_sub.id)

    ##########
    # Invoice CRUD
    def test_create_invoice_success(self):
        stripe_cus_norrin_radd = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)
        
        stripe_payment_method = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PAYMENT_METHOD, **self.payment_method)
        setup_intent_object = {
            'customer': stripe_cus_norrin_radd.id,
            'confirm': True,
            'payment_method_types': ['card'],
            'payment_method': stripe_payment_method.id,
            'metadata': self.valid_metadata
        }
        stripe_setup_intent = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.SETUP_INTENT, **setup_intent_object)
        
        
        stripe_pro_monthly = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **self.pro_monthly_license)
        self.pri_monthly['product'] = stripe_pro_monthly.id
        stripe_price = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRICE, **self.pri_monthly)
        
        subscription_obj = {
            'customer': stripe_cus_norrin_radd.id,
            'items': [{'price': stripe_price.id}],
            'default_payment_method': stripe_payment_method.id,
            'metadata': self.valid_metadata,

        }
        stripe_sub = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.SUBSCRIPTION, **subscription_obj)
            
        stripe_invoice_object = {
            'metadata': self.valid_metadata,
            'subscription': stripe_sub.id,
            'customer': stripe_cus_norrin_radd.id,
            'statement_descriptor': 'Test description'
        }

        stripe_invoice = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.INVOICE, **stripe_invoice_object)

        self.assertIsNotNone(stripe_invoice.id)
        
    ##########
    # Setup Intent CRUD
    def test_create_setup_intent_success(self):
        stripe_cus_norrin_radd = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **self.cus_norrin_radd)
        stripe_payment_method = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PAYMENT_METHOD, **self.payment_method)
        
        setup_intent_object = {
            'customer': stripe_cus_norrin_radd.id,
            'confirm': True,
            'payment_method_types': ['card'],
            'payment_method': stripe_payment_method.id,
            'metadata': self.valid_metadata
        }

        stripe_setup_intent = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.SETUP_INTENT, **setup_intent_object)
        
        self.assertIsNotNone(stripe_setup_intent.id)