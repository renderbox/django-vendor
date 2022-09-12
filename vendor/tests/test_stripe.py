import stripe

from django.conf import settings
from django.test import TestCase, Client, tag
from django.contrib.sites.models import Site
from siteconfigs.models import SiteConfigModel
from unittest import skipIf
from vendor.models import CustomerProfile, Offer
from vendor.processors import StripeProcessor


@skipIf((settings.STRIPE_PUBLIC_KEY or settings.STRIPE_SECRET_KEY) is None, "Strip enviornment variables not set, skipping tests")
class StripeProcessorTests(TestCase):
    fixtures = ['user', 'unit_test']

    VALID_CARD_NUMBERS = [
        '4242424242424242',  # visa
        '4000056655665556',  # visa debit
        '5555555555554444',  # mastercard
        '5200828282828210',  # mastercard debit
    ]

    def setup_processor_site_config(self):
        self.processor_site_config = SiteConfigModel()
        self.processor_site_config.site = self.existing_invoice.site
        self.processor_site_config.key = 'vendor.config.PaymentProcessorSiteConfig'
        self.processor_site_config.value = {"payment_processor": "stripe.StripeProcessor"}
        self.processor_site_config.save()

    def setup_user_client(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def setup_existing_invoice(self):
        t_shirt = Product.objects.get(pk=1)
        t_shirt.meta['msrp']['usd'] = randrange(1, 1000)
        t_shirt.save()
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
        self.processor = StripeProcessor(self.site, self.existing_invoice)
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
                'card_number': '4242424242424242',
                'expire_month': '12',
                'expire_year': '2030',
                'cvv_number': '900',
                'payment_type': '10'
            }
        }

    def test_environment_variables_set(self):
        self.assertIsNotNone(settings.STRIPE_PUBLIC_KEY)

    def test_processor_initialization_success(self):
        self.assertEquals(self.processor.provider, 'StripeProcessor')
        self.assertIsNotNone(self.processor.invoice)
        self.assertIsNotNone(self.processor.credentials)

    def test_process_payment_transaction_success(self):
        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)
        self.processor.set_stripe_payment_source()
        self.processor.invoice.total = randrange(1, 1000)
        for recurring_order_items in self.processor.invoice.get_recurring_order_items():
            self.processor.invoice.remove_offer(recurring_order_items.offer)

        self.processor.authorize_payment()
        self.assertIsNotNone(self.processor.payment)
        self.assertTrue(self.processor.payment.success)
        self.assertEquals(InvoiceStatus.COMPLETE, self.processor.invoice.status)

    def test_process_payment_transaction_fail_invalid_card(self):
        """
        Simulates a payment transaction for a reqeust.POST, with the payment and
        billing information. The test send an invalid card number to test the
        transation fails
        """
        self.form_data['credit_card_form']['card_number'] = '4242424242424241'

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

    def test_process_payment_fail_cvv_no_match(self):
        """
        Check incorrect cvc. Will fail with card number 4000000000000127
        """
        self.form_data['credit_card_form']['cvv_number'] = '901'
        self.form_data['credit_card_form']['card_number'] = '4000000000000127'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_submitted)

    def test_process_payment_generic_decline(self):
        """
        Check a failed transaction due to to generic decline
        """
        self.form_data['credit_card_form']['cvv_number'] = '902'
        self.form_data['credit_card_form']['card_number'] = '4000000000000002'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_submitted)

    def test_process_payment_fail_cvv_check_fails(self):
        """
        CVC number check fails for any cvv number passed
        """
        self.form_data['credit_card_form']['cvv_number'] = '903'
        self.form_data['credit_card_form']['card_number'] = '4000000000000101'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_submitted)

    def test_process_payment_fail_expired_card(self):
        """
        Payment fails because of expired card
        """
        self.form_data['credit_card_form']['cvv_number'] = '904'
        self.form_data['credit_card_form']['card_number'] = '4000000000000069'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_submitted)

    def test_process_payment_fail_fraud_always_blocked(self):
        """
        Fraud prevention fail: Always blocked
        """
        self.form_data['credit_card_form']['cvv_number'] = '903'
        self.form_data['credit_card_form']['card_number'] = '4000000000000101'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_submitted)

    def test_process_payment_fail_fraud_higest_risk(self):
        """
        Fraud prevention fail: Higest Risk
        """
        self.form_data['credit_card_form']['cvv_number'] = '903'
        self.form_data['credit_card_form']['card_number'] = '4000000000004954'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_submitted)

    def test_process_payment_fail_fraud_elevated_risk(self):
        """
        Fraud prevention fail : Elevated risk
        """
        self.form_data['credit_card_form']['cvv_number'] = '903'
        self.form_data['credit_card_form']['card_number'] = '4000000000009235'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_submitted)

    def test_process_payment_postal_code_check_fails(self):
        """
        Postal code check fails for any code given fo this card number
        """

        self.form_data['credit_card_form']['card_number'] = '4000000000000036'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_submitted)


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
        self.site = Site.objects.get(pk=1)
        self.init_test_objects()
        self.processor = StripeProcessor(self.site)

    def test_create_stripe_object_with_site_metadata_success(self):
        del(self.cus_norrin_radd['metadata'])

        stripe_customer = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)
        self.assertIn('site', stripe_customer.metadata)

    ##########
    # Customer CRUD
    def test_create_customer_success(self):
        stripe_customer = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)
        
        self.assertIsNotNone(stripe_customer.id)
        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer.id)

    def test_create_customer_with_address_success(self):
        self.cus_norrin_radd['address'] = self.valid_addr

        stripe_customer = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)
        
        self.assertIsNotNone(stripe_customer.id)
        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer.id)

    ##########
    # Product CRUD
    def test_create_product_success(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)

        self.assertIsNotNone(stripe_product.id)
        self.processor.stripe_call(stripe.Product.delete, stripe_product.id)
        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product.id)

    def test_create_product_no_name_fail(self):
        del(self.pro_monthly_license['name'])
        
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_monthly_license)
        self.assertFalse(self.processor.transaction_submitted)

    ##########
    # Price CRUD
    def test_create_price_product_data_success(self):
        del(self.pro_monthly_license['metadata'])
        self.pri_monthly['product_data'] = self.pro_monthly_license

        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, self.pri_monthly)

        self.assertIsNotNone(stripe_price.id)

    def test_create_price_product_id_success(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.self.pro_annual_license)
        self.pri_monthly['product'] = stripe_product.id

        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, self.pri_monthly)

        self.assertIsNotNone(stripe_price.id)

    def test_create_price_invalid_field_fail(self):
        self.pri_monthly['type'] = "This is not a valid field"

        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, self.pri_monthly)
        
        self.assertFalse(self.processor.transaction_submitted)

    ##########
    # Coupon CRUD
    def test_create_coupon_success(self):
        stripe_coupon = self.processor.stripe_create_object(self.processor.stripe.Coupon, self.cou_first_month_free)

        self.assertIsNotNone(stripe_coupon.id)
        stripe_coupon = self.processor.stripe_delete_object(self.processor.stripe.Coupon, stripe_coupon.id)

    ##########
    # Subscription CRUD
    def test_create_subscription_success(self):
        stripe_cus_norrin_radd = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)
        
        stripe_payment_method = self.processor.stripe_create_object(self.processor.stripe.PaymentMethod, self.payment_method)

        setup_intent_object = {
            'customer': stripe_cus_norrin_radd.id,
            'confirm': True,
            'payment_method_types': ['card'],
            'payment_method': stripe_payment_method.id,
            'metadata': self.valid_metadata
        }
        stripe_setup_intent = self.processor.stripe_create_object(self.processor.stripe.SetupIntent, setup_intent_object)
        
        stripe_pro_monthly = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_monthly_license)
        
        self.pri_monthly['product'] = stripe_pro_monthly.id
        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, self.pri_monthly)
        
        subscription_obj = {
            'customer': stripe_cus_norrin_radd.id,
            'items': [{'price': stripe_price.id}],
            'default_payment_method': stripe_payment_method.id,
            'metadata': self.valid_metadata,

        }
        stripe_subscription = self.processor.stripe_create_object(self.processor.stripe.Subscription, subscription_obj)

        self.assertIsNotNone(stripe_subscription.id)

    ##########
    # Invoice CRUD
    # def test_create_invoice_success(self):
        
        # setup_intent_object = {
        #     'customer': stripe_cus_norrin_radd.id,
        #     'confirm': True,
        #     'payment_method_types': ['card'],
        #     'payment_method': stripe_payment_method.id,
        #     'metadata': self.valid_metadata
        # }
        
        
        # self.pri_monthly['product'] = stripe_pro_monthly.id
        
        # subscription_obj = {
        #     'customer': stripe_cus_norrin_radd.id,
        #     'items': [{'price': stripe_price.id}],
        #     'default_payment_method': stripe_payment_method.id,
        #     'metadata': self.valid_metadata,

        # }
            
        # stripe_invoice_object = {
        #     'metadata': self.valid_metadata,
        #     'subscription': stripe_sub.id,
        #     'customer': stripe_cus_norrin_radd.id,
        #     'statement_descriptor': 'Test description'
        # }


        # self.assertIsNotNone(stripe_invoice.id)
        
    ##########
    # Setup Intent CRUD
    def test_create_setup_intent_success(self):

        stripe_cus_norrin_radd = self.processor.stripe_create_object(self.processor.stripe.Customer, cus_norrin_radd)
        stripe_payment_method = self.processor.stripe_create_object(self.processor.stripe.PaymentMethod, payment_method)
        
        setup_intent_object = {
            'customer': stripe_cus_norrin_radd.id,
            'confirm': True,
            'payment_method_types': ['card'],
            'payment_method': stripe_payment_method.id,
            'metadata': self.valid_metadata
        }
        stripe_setup_intent = self.processor.stripe_create_object(self.processor.stripe.SetupIntent, setup_intent_object)
        
        self.assertIsNotNone(stripe_setup_intent.id)

    
    class StripeBuildObjectTests(TestCase):

        fixtures = ['user', 'unit_test']

        def setUp(self):
            stripe.api_key = settings.STRIPE_PUBLIC_KEY
            self.site = Site.objects.get(pk=1)
            self.processor = StripeProcessor(self.site)


        def test_build_customer_success(self):
            customer_profile = CustomerProfile.objects.all().first()

            stripe_customer = self.processor.build_customer(customer_profile)
            
            self.assertIsNotNone(stripe_customer.id)
            self.assertEqual(f"{customer_profile.user.first_name} {customer_profile.user.last_name}", stripe_customer.name)
            self.assertEqual(customer_profile.user.email, stripe_customer.email)

        def test_build_product_success(self):
            offer = Offer.objects.all().first()

            stripe_product = self.processor.build_product(offer)

            self.assertIsNotNone(stripe_product.id)
            self.assertEqual(offer.name, stripe_product.name)

        def test_build_price_success(self):
            offer = Offer.objects.all().first()

            stripe_product = self.processor.build_product(offer)
            price = offer.prices.first()
            stripe_price = self.processor.build_price(offer, price)

            self.assertIsNotNone(stripe_price.id)
            self.assertEqual(price.cost, stripe_price.unit_amount)


        def test_build_coupon_success(self):
            offer = Offer.objects.all().first()
            price = offer.prices.first()

            stripe_coupon = self.processor.build_coupon(offer, price)
            
            self.assertIsNotNone(stripe_coupon.id)
            self.assertEqual(stripe_coupon.amount_off, (offer.get_msrp(self) - price.cost))

        def test_build_subscription_success(self):
            pass

        def test_build_payment_method_successs(self):
            pass

        def test_build_setup_intent_success(self):
            pass

