import stripe
from random import randrange
from django.conf import settings
from django.test import TestCase, Client, tag
from django.contrib.sites.models import Site
from django.db.models import signals
from django.utils import timezone
from django.db.models import Q
from siteconfigs.models import SiteConfigModel
from unittest import skipIf
from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.processors import StripeProcessor
from vendor.config import DEFAULT_CURRENCY
from django.contrib.auth import get_user_model
from vendor.models import Invoice, Payment, Offer, Price, Receipt, CustomerProfile, OrderItem, Subscription
from core.models import Product
from vendor.models.choice import InvoiceStatus


User = get_user_model()

@skipIf((settings.STRIPE_PUBLIC_KEY or settings.STRIPE_SECRET_KEY) is None, "Stripe enviornment variables not set, skipping tests")
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
        self.site.domain = 'sc'
        self.site.save()
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
        self.valid_metadata = {'site': self.site.domain}
        self.valid_addr = {'city': "na", 'country': "US", 'line1': "Salvatierra walk", 'postal_code': "90321",
                           'state': 'CA'}

        self.cus_norrin_radd = {'name': 'Norrin Radd', 'email': 'norrin@radd.com', 'metadata': self.valid_metadata}
        self.cus_norrin_radd2 = {'name': 'Jake Paul', 'email': 'jpaul@radd.com', 'metadata': self.valid_metadata}
        self.pro_annual_license = {"name": "Annual Subscription", 'metadata': self.valid_metadata}
        self.pro_annual_license2 = {"name": "Annual Subscription 2", 'metadata': self.valid_metadata}
        self.pri_monthly = {"currency": "usd", "unit_amount": 1024,
                            "recurring": {"interval": "month", "interval_count": 1, "usage_type": "licensed"},
                            'metadata': self.valid_metadata}

    def test_environment_variables_set(self):
        self.assertIsNotNone(settings.STRIPE_PUBLIC_KEY)

    def test_processor_initialization_success(self):
        self.assertEquals(self.processor.provider, 'StripeProcessor')
        self.assertIsNotNone(self.processor.invoice)
        self.assertIsNotNone(self.processor.credentials)

    def test_process_payment_transaction_success(self):
        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)
        self.processor.invoice.total = randrange(1, 1000)
        for recurring_order_items in self.processor.invoice.get_recurring_order_items():
            self.processor.invoice.remove_offer(recurring_order_items.offer)

        self.processor.set_stripe_payment_source()
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
        self.assertFalse(self.processor.transaction_succeded)
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
        self.assertFalse(self.processor.transaction_succeded)
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
        self.assertFalse(self.processor.transaction_succeded)

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
        self.assertFalse(self.processor.transaction_succeded)

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
        self.assertFalse(self.processor.transaction_succeded)

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
        self.assertFalse(self.processor.transaction_succeded)

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
        self.assertFalse(self.processor.transaction_succeded)

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
        self.assertFalse(self.processor.transaction_succeded)

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
        self.assertFalse(self.processor.transaction_succeded)

    def test_process_payment_postal_code_check_fails(self):
        """
        Postal code check fails for any code given fo this card number
        """

        self.form_data['credit_card_form']['card_number'] = '4000000000000036'

        self.processor.set_billing_address_form_data(self.form_data.get('billing_address_form'), BillingAddressForm)
        self.processor.set_payment_info_form_data(self.form_data.get('credit_card_form'), CreditCardForm)

        self.processor.invoice.total = randrange(1, 1000)
        self.processor.authorize_payment()
        self.assertFalse(self.processor.transaction_succeded)

    def test_build_search_query_name(self):
        """
        Check our query string for stripe searches are valid
        """
        valid_query = 'name:"Johns Offer"'

        name_clause = self.processor.query_builder.make_clause_template(
            field='name',
            value='Johns Offer',
            operator=self.processor.query_builder.EXACT_MATCH
        )

        query = self.processor.query_builder.build_search_query(self.processor.stripe.Product, [name_clause])
        self.assertEquals(valid_query, query)

    def test_build_search_query_name_and_metadata(self):
        """
        Check our query string for stripe searches are valid
        """
        valid_query = 'name:"Johns Offer" AND metadata["site"]:"site4"'

        name_clause = self.processor.query_builder.make_clause_template(
            field='name',
            value='Johns Offer',
            operator=self.processor.query_builder.EXACT_MATCH,
            next_operator=self.processor.query_builder.AND
        )
        metadata_clause = self.processor.query_builder.make_clause_template(
            field='metadata',
            key='site',
            value='site4',
            operator=self.processor.query_builder.EXACT_MATCH
        )

        query = self.processor.query_builder.build_search_query(self.processor.stripe.Product, [name_clause, metadata_clause])
        self.assertEquals(valid_query, query)

    def test_build_search_query_metadata(self):
        """
        Check our query string for stripe searches are valid
        """
        valid_query = 'metadata["pk"]:4'

        metadata_clause = self.processor.query_builder.make_clause_template(
            field='metadata',
            key='pk',
            value=4,
            operator=self.processor.query_builder.EXACT_MATCH
        )

        query = self.processor.query_builder.build_search_query(self.processor.stripe.Product, [metadata_clause])
        self.assertEquals(valid_query, query)

    def test_build_search_query_metadata_fail(self):
        """
        Check metadata doesnt create query without key
        """

        metadata_clause = self.processor.query_builder.make_clause_template(
            field='metadata',
            value='site4',
            operator=self.processor.query_builder.EXACT_MATCH
        )

        query = self.processor.query_builder.build_search_query(self.processor.stripe.Product, [metadata_clause])
        self.assertEquals(query, "")

    def test_get_stripe_offers(self):
        # TODO I think there is a delay in the ability to search an object after its been created

        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)
        stripe_product2 = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license2)

        current_stripe_offers = self.processor.get_site_offers(self.site)
        offer_names = [offer.name for offer in current_stripe_offers]

        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product.id)
        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product2.id)

        self.assertIsNotNone(current_stripe_offers)
        self.assertIn(stripe_product.name, offer_names)
        self.assertIn(stripe_product2.name, offer_names)

    def test_get_vendor_offers_in_stripe(self):
        offer1 = Offer.objects.create(site=self.site, name=self.pro_annual_license['name'], start_date=timezone.now())
        offer2 = Offer.objects.create(site=self.site, name=self.pro_annual_license2['name'], start_date=timezone.now())
        
        self.pro_annual_license['metadata']['pk'] = offer1.pk
        self.pro_annual_license2['metadata']['pk'] = offer2.pk
        
        stripe_product1 = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)
        stripe_product2 = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license2)

        offers = self.processor.get_site_offers(self.site)
        pk_list = [product['metadata']['pk'] for product in offers]
        vendor_offers_in_stripe = self.processor.get_vendor_offers_in_stripe(pk_list, self.site)

        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product1.id)
        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product2.id)

        self.assertIsNotNone(vendor_offers_in_stripe)
        self.assertEquals(vendor_offers_in_stripe.count(), 2)

    def test_get_vendor_offers_not_in_stripe(self):
        stripe_product1 = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)
        stripe_product2 = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license2)

        offers = self.processor.get_site_offers(self.site)
        pk_list = [product['metadata']['pk'] for product in offers]
        vendor_offers_not_in_stripe = self.processor.get_vendor_offers_not_in_stripe(pk_list, self.site)

        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product1.id)
        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product2.id)

        self.assertIsNotNone(vendor_offers_not_in_stripe)

    def test_get_stripe_customers(self):
        stripe_customer1 = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)
        stripe_customer2 = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd2)

        current_stripe_customers = self.processor.get_stripe_customers(self.site)
        customer_names = [customer.name for customer in current_stripe_customers]

        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer1.id)
        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer2.id)

        self.assertIsNotNone(current_stripe_customers)
        self.assertIn(stripe_customer1.name, customer_names)
        self.assertIn(stripe_customer2.name, customer_names)


    def test_get_vendor_customers_in_stripe(self):
        first_name1, last_name1 = self.cus_norrin_radd['name'].split(' ')
        first_name2, last_name2 = self.cus_norrin_radd2['name'].split(' ')
        user1 = User.objects.create(email=self.cus_norrin_radd['email'], first_name=first_name1, last_name=last_name1, username='test1')
        user2 = User.objects.create(email=self.cus_norrin_radd2['email'], first_name=first_name2, last_name=last_name2, username='test2')
        stripe_customer1 = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)
        stripe_customer2 = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd2)
        vendor_customer1 = CustomerProfile.objects.create(site=self.site, user=user1)
        vendor_customer2 = CustomerProfile.objects.create(site=self.site, user=user2)

        current_stripe_customers = self.processor.get_stripe_customers(self.site)
        email_list = [customer.email for customer in current_stripe_customers]
        customers_in_vendor = self.processor.get_vendor_customers_in_stripe(email_list, self.site)

        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer1.id)
        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer2.id)

        self.assertIsNotNone(customers_in_vendor)
        self.assertEquals(customers_in_vendor.count(), 2)

    def test_get_vendor_customers_not_in_stripe(self):
        stripe_customer1 = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)
        stripe_customer2 = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd2)

        current_stripe_customers = self.processor.get_stripe_customers(self.site)
        email_list = [customer.email for customer in current_stripe_customers]
        customers_not_in_vendor = self.processor.get_vendor_customers_not_in_stripe(email_list, self.site)

        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer1.id)
        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer2.id)

        self.assertIsNotNone(customers_not_in_vendor)

    def test_create_stripe_customers(self):
        first_name1, last_name1 = self.cus_norrin_radd['name'].split(' ')
        first_name2, last_name2 = self.cus_norrin_radd2['name'].split(' ')
        user1 = User.objects.create(email=self.cus_norrin_radd['email'], first_name=first_name1, last_name=last_name1, username='test1')
        user2 = User.objects.create(email=self.cus_norrin_radd2['email'], first_name=first_name2, last_name=last_name2, username='test2')
        vendor_customer1 = CustomerProfile.objects.create(site=self.site, user=user1)
        vendor_customer2 = CustomerProfile.objects.create(site=self.site, user=user2)

        vendor_customers_not_in_stripe = [vendor_customer1, vendor_customer2]

        self.processor.create_stripe_customers(vendor_customers_not_in_stripe)

        vendor_customer1 = CustomerProfile.objects.get(site=self.site, user=user1)
        vendor_customer2 = CustomerProfile.objects.get(site=self.site, user=user2)

        self.processor.stripe_delete_object(self.processor.stripe.Customer, vendor_customer1.meta['stripe_id'])
        self.processor.stripe_delete_object(self.processor.stripe.Customer, vendor_customer2.meta['stripe_id'])

        self.assertIsNotNone(vendor_customer1.meta.get('stripe_id', None))
        self.assertIsNotNone(vendor_customer2.meta.get('stripe_id', None))


    def test_update_stripe_customers(self):
        stripe_customer1 = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)
        stripe_customer2 = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd2)

        user1 = User.objects.create(email=self.cus_norrin_radd['email'], first_name='New First Name1', last_name='Last Name1', username='test1')
        user2 = User.objects.create(email=self.cus_norrin_radd2['email'], first_name='New First Name2', last_name='Last Name2', username='test2')
        vendor_customer1 = CustomerProfile.objects.create(site=self.site, user=user1, meta={'stripe_id': stripe_customer1.id})
        vendor_customer2 = CustomerProfile.objects.create(site=self.site, user=user2, meta={'stripe_id': stripe_customer2.id})
        vendor_customers_in_stripe = [vendor_customer1, vendor_customer2]

        self.processor.update_stripe_customers(vendor_customers_in_stripe)

        updated_stripe_customer1 = self.processor.stripe_get_object(self.processor.stripe.Customer, stripe_customer1.id)
        updated_stripe_customer2 = self.processor.stripe_get_object(self.processor.stripe.Customer, stripe_customer2.id)

        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer1.id)
        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer2.id)

        self.assertEquals(updated_stripe_customer1.name, f'{user1.first_name} {user1.last_name}')
        self.assertEquals(updated_stripe_customer2.name, f'{user2.first_name} {user2.last_name}')

    def test_check_product_does_exist(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)
        metadata = {
                'key': 'site',
                'value': 'site4',
                'field': 'metadata'
        }
        product = self.processor.does_product_exist(self.pro_annual_license['name'], metadata=metadata)

        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product.id)

        self.assertIsNotNone(product)

    def test_get_product_id_with_name(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)
        metadata = {
            'key': 'site',
            'value': self.site.domain,
            'field': 'metadata'
        }
        product_id = self.processor.get_product_id_with_name(self.pro_annual_license['name'], metadata=metadata)

        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product.id)

        self.assertEquals(stripe_product.id, product_id)


    """
    Commenting out since stripe doesnt allow you to delete Price objects (weird)
    
    def test_check_price_does_exist(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)
        self.pri_monthly['product'] = stripe_product.id
        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, self.pri_monthly)

        metadata = {
            'key': 'site',
            'value': 'site4',
            'field': 'metadata'
        }
        price = self.processor.does_price_exist(self.pri_monthly['product'], metadata=metadata)

        self.assertIsNotNone(price)


        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product.id)
        self.processor.stripe_delete_object(self.processor.stripe.Price, stripe_price.id)"""

    def test_sync_customers(self):
        # Vendor objects not in stripe so create them there
        signals.post_save.disconnect(receiver=signals.post_save, sender=CustomerProfile)
        user = User.objects.get(pk=1)
        customer = CustomerProfile.objects.create(site=self.site, user=user)

        self.processor.sync_customers(customer.site)

        customer.refresh_from_db()

        stripe_id = customer.meta.get('stripe_id')

        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_id)
        self.assertTrue(stripe_id)

    def test_sync_offers(self):
        signals.post_save.disconnect(receiver=signals.post_save, sender=CustomerProfile)
        now = timezone.now()

        offer = Offer.objects.create(site=self.site, name='Stripe Offer', start_date=now)
        product = Product.objects.create(name='Stripe Product', site=self.site)
        product.offers.add(offer)
        price = Price.objects.create(offer=offer, cost=10.99, start_date=timezone.now())

        # clear offers that dont have a price, since we cant create stripe product and price
        offers_with_no_price = Offer.objects.filter(Q(site=offer.site), Q(prices=None) | Q(prices__start_date__lte=now))
        offers_with_no_price.delete()

        self.processor.sync_offers(offer.site)

        offer.refresh_from_db()
        stripe_meta = offer.meta.get('stripe')

        #deleted_price = self.processor.stripe_delete_object(self.processor.stripe.Price,
        #                                                    stripe_meta.get('price_id'))
        #deleted_offer = self.processor.stripe_delete_object(self.processor.stripe.Product,
        #                                                    stripe_meta.get('product_id'))

        self.assertTrue(stripe_meta)
        self.assertTrue(stripe_meta.get('product_id'))
        self.assertTrue(stripe_meta.get('price_id'))
        self.assertTrue(stripe_meta.get('coupon_id'))




@skipIf((settings.STRIPE_PUBLIC_KEY or settings.STRIPE_SECRET_KEY) is None, "Strip enviornment variables not set, skipping tests")
class StripeCRUDObjectTests(TestCase):

    def init_test_objects(self):
        self.valid_metadata = {'site': 'sc'}
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
        self.site.domain = 'sc'
        self.site.save()
        self.init_test_objects()
        self.processor = StripeProcessor(self.site)

    ##########
    # Customer CRUD
    def test_create_customer_success(self):
        stripe_customer = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)

        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer.id)

        self.assertIsNotNone(stripe_customer.id)


    def test_create_customer_with_address_success(self):
        self.cus_norrin_radd['address'] = self.valid_addr

        stripe_customer = self.processor.stripe_create_object(self.processor.stripe.Customer, self.cus_norrin_radd)

        self.processor.stripe_delete_object(self.processor.stripe.Customer, stripe_customer.id)

        self.assertIsNotNone(stripe_customer.id)


    ##########
    # Product CRUD
    def test_create_product_success(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)
        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product.id)

        self.assertIsNotNone(stripe_product.id)

    def test_create_product_no_name_fail(self):
        del(self.pro_monthly_license['name'])
        
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_monthly_license)
        self.assertFalse(self.processor.transaction_succeded)

    def test_get_product_success(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)

        self.assertIsNotNone(stripe_product.id)

        fetch_product = self.processor.stripe_get_object(self.processor.stripe.Product, stripe_product.id)

        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product.id)

        self.assertIsNotNone(fetch_product.id)

    def test_update_product_success(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)

        self.assertIsNotNone(stripe_product.id)

        update_data = {"name": "Annual Subscription 2"}
        update_product = self.processor.stripe_update_object(self.processor.stripe.Product, stripe_product.id, update_data)

        self.processor.stripe_delete_object(self.processor.stripe.Product, stripe_product.id)

        self.assertIsNotNone(update_product.id)
        self.assertEquals(update_product['name'], update_data['name'])


    ##########
    # Price CRUD
    def test_create_price_product_data_success(self):
        del(self.pro_monthly_license['metadata'])
        self.pri_monthly['product_data'] = self.pro_monthly_license

        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, self.pri_monthly)

        self.assertIsNotNone(stripe_price.id)

    def test_create_price_product_id_success(self):
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, self.pro_annual_license)
        self.pri_monthly['product'] = stripe_product.id

        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, self.pri_monthly)

        self.assertIsNotNone(stripe_price.id)

    def test_create_price_invalid_field_fail(self):
        self.pri_monthly['type'] = "This is not a valid field"

        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, self.pri_monthly)
        
        self.assertFalse(self.processor.transaction_succeded)

    ##########
    # Coupon CRUD
    def test_create_coupon_success(self):
        stripe_coupon = self.processor.stripe_create_object(self.processor.stripe.Coupon, self.cou_first_month_free)

        stripe_coupon = self.processor.stripe_delete_object(self.processor.stripe.Coupon, stripe_coupon.id)

        self.assertIsNotNone(stripe_coupon.id)

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
        
        self.assertIsNotNone(stripe_setup_intent.id)


@skipIf((settings.STRIPE_PUBLIC_KEY or settings.STRIPE_SECRET_KEY) is None, "Strip enviornment variables not set, skipping tests")
class StripeBuildObjectTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        stripe.api_key = settings.STRIPE_PUBLIC_KEY
        self.site = Site.objects.get(pk=1)
        self.site.domain = 'sc'
        self.site.save()
        self.processor = StripeProcessor(self.site)

    def test_build_customer_success(self):
        customer_profile = CustomerProfile.objects.all().first()

        customer_data = self.processor.build_customer(customer_profile)
        stripe_customer = self.processor.stripe_create_object(self.processor.stripe.Customer, customer_data)
        
        self.assertIsNotNone(stripe_customer.id)
        self.assertEqual(f"{customer_profile.user.first_name} {customer_profile.user.last_name}", stripe_customer.name)
        self.assertEqual(customer_profile.user.email, stripe_customer.email)

    def test_build_product_success(self):
        offer = Offer.objects.all().first()

        product_data = self.processor.build_product(offer)
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, product_data)

        self.assertIsNotNone(stripe_product.id)
        self.assertEqual(offer.name, stripe_product.name)

    def test_build_price_success(self):
        offer = Offer.objects.all().first()

        product_data = self.processor.build_product(offer)
        stripe_product = self.processor.stripe_create_object(self.processor.stripe.Product, product_data)

        offer.meta['stripe'] = {
            'product_id': stripe_product.id
        }
        offer.save()

        price = offer.get_current_price_instance() if offer.get_current_price_instance() else None
        msrp = offer.get_msrp()
        current_price = msrp
        price_pk = None
        if price:
            current_price = price.cost
            price_pk = price.pk

        price_data = self.processor.build_price(offer, msrp, current_price, DEFAULT_CURRENCY, price_pk)
        stripe_price = self.processor.stripe_create_object(self.processor.stripe.Price, price_data)

        self.assertIsNotNone(stripe_price.id)
        self.processor.stripe_update_object(self.processor.stripe.Price, stripe_price.id, {'active':False})
        self.assertEqual(price.cost, stripe_price.unit_amount)

    def test_build_coupon_success(self):
        offer = Offer.objects.all().first()
        price = offer.prices.first()

        coupon_data = self.processor.build_coupon(offer, DEFAULT_CURRENCY)
        stripe_coupon = self.processor.stripe_create_object(self.processor.stripe.Coupon, coupon_data)
        
        self.assertIsNotNone(stripe_coupon.id)
        self.processor.stripe_delete_object(self.processor.stripe.Coupon, stripe_coupon.id)
        self.assertEqual("".join([str(stripe_coupon.amount_off)[:-2], ".", str(stripe_coupon.amount_off)[-2:]]), str((offer.get_msrp() - price.cost)))

    def test_build_subscription_success(self):
        pass

    def test_build_payment_method_successs(self):
        pass

    def test_build_setup_intent_success(self):
        pass

