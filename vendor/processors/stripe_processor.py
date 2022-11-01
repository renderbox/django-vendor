"""
Payment processor for Stripe.
"""
import logging
import uuid
import stripe
from django.conf import settings
from .base import PaymentProcessorBase
from vendor.models.choice import (
    SubscriptionStatus,
    TransactionTypes,
    PaymentTypes,
    TermType,
    TermDetailUnits,
    InvoiceStatus,
    PurchaseStatus
)
from vendor.integrations import StripeIntegration
from vendor.models import Offer, CustomerProfile
from django.contrib.sites.models import Site
from vendor.config import DEFAULT_CURRENCY



logger = logging.getLogger(__name__)

# def add_site_on_object_metadata(func):
#     # Decorate that check if the stripe object data has a metadata field that has site field.
#     # If it does not have one it addas it to kwargs
#     def wrapper(*args, **kwargs):
#         if 'metadata' not in kwargs or 'site' not in kwargs['metadata']:
#             kwargs['metadata'] = {'site': args[0].site}

#         return func(*args, kwargs)
    
#     return wrapper

class StripeQueryBuilder:
    """
    Query builder that adheres to Stripe search rules found here https://stripe.com/docs/search

    Ex:
    To generate a query like 'name:"Johns Offer" AND metadata["site"]:"site4"'

    query_builder = StripeQueryBuilder()

    name_clause = query_builder.make_clause_template()
    name_clause['field'] = 'name'
    name_clause['value'] = 'Johns Offer'
    name_clause['operator'] = query_builder.EXACT_MATCH
    name_clause['next_operator'] = query_builder.AND

    metadata_clause = query_builder.make_clause_template()
    metadata_clause['field'] = 'metadata'
    metadata_clause['key'] = 'site'
    metadata_clause['value'] = 'site4'
    metadata_clause['operator'] = query_builder.EXACT_MATCH

    query = query_builder.build_search_query(processor.stripe.Product, [name_clause, metadata_clause])


    """

    # Search syntax
    EXACT_MATCH = ':'
    AND = 'AND'
    OR = 'OR'
    EXCLUDE = '-'
    NULL = 'NULL'
    SUBSTRING_MATCH = '~'
    GREATER_THAN = '>'
    LESS_THAN = '<'
    EQUALS = '='
    GREATER_THAN_OR_EQUAL_TO = '>='
    LESS_THAN_OR_EQUAL_TO = '<='

    # Valid fields
    VALID_FIELDS = {
        'charge': [
            'amount',
            'billing_details.address.postal_code',
            'created',
            'currency',
            'customer',
            'disputed',
            'metadata',
            'payment_method_details.card.last4',
            'payment_method_details.card.exp_month',
            'payment_method_details.card.exp_year',
            'payment_method_details.card.brand',
            'payment_method_details.card.fingerprint',
            'refunded',
            'status'
        ],
        'customer': [
            'created',
            'email',
            'metadata',
            'name',
            'phone'
        ],
        'invoice': [
            'created',
            'currency',
            'customer',
            'metadata',
            'number',
            'receipt_number',
            'subscription',
            'total'
        ],
        'paymentintent': [
            'amount',
            'created',
            'currency',
            'customer',
            'metadata',
            'status',
        ],
        'price': [
            'active',
            'lookup_key',
            'currency',
            'product',
            'metadata',
            'type',
        ],
        'product': [
            'active',
            'description',
            'name',
            'shippable',
            'metadata',
            'url',
        ],
        'subscription': [
            'created',
            'metadata',
            'status',
        ],
    }

    def make_clause_template(self, field=None, operator=None, key=None, value=None, next_operator=None):
        return {
            'field': field,
            'operator': operator,
            'key': key,
            'value': value,
            'next_operator': next_operator
        }

    def is_valid_field(self, stripe_object_class, field):
        return field in self.VALID_FIELDS[stripe_object_class.__name__.lower()]

    def search_clause_checks_pass(self, clause_obj):
        """
        All checks should be added here to make sure the caller isnt missing required params
        """
        if clause_obj.get('field', None) == 'metadata':
            if not clause_obj.get('key', None):
                logger.error(f'StripeQueryBuilder.search_clause_checks_pass: metadata searches need a key field')
                return False

        # TODO add more checks

        return True

    def build_search_query(self, stripe_object_class, search_clauses):
        query = ""

        if not isinstance(search_clauses, list):
            logger.error(f'Passed in params {search_clauses} is not a list of search clauses (dicts)')
            return query

        if not len(search_clauses) > 0:
            logger.error(f'Passed in search clauses {search_clauses} cannot be empty')
            return query

        for query_obj in search_clauses:
            field = query_obj.get('field', None)
            operator = query_obj.get('operator', None)
            key = query_obj.get('key', None)
            value = query_obj.get('value', None)
            next_operator = query_obj.get('next_operator', None)

            if not self.search_clause_checks_pass(query_obj):
                logger.error(f'StripeQueryBuilder.build_search_query: search clause {query_obj} is not valid')
                return query

            if self.is_valid_field(stripe_object_class, field):
                if not key:
                    # not metadata
                    if isinstance(value, str):
                        query += f'{field}{operator}"{value}"'
                    else:
                        query += f'{field}{operator}{value}'
                else:
                    # is metadata
                    if isinstance(value, str):
                        query += f'{field}["{key}"]{operator}"{value}"'
                    else:
                        query += f'{field}["{key}"]{operator}{value}'

                if next_operator:
                    # space, AND, OR
                    query += f' {next_operator} '

            else:
                logger.error(f'StripeQueryBuilder.build_search_query: {field} is not valid for {stripe_object_class}')
                return query

        return query


class StripeProcessor(PaymentProcessorBase):
    """ 
    Implementation of Stripe SDK
    https://self.stripe.com/docs/api/authentication?lang=python
    """

    TRANSACTION_SUCCESS_MESSAGE = 'message'
    TRANSACTION_SUCCESS_CODE = 'code'
    TRANSACTION_FAIL_MESSAGE = 'error_text'
    TRANSACTION_FAIL_CODE = 'error_code'
    TRANSACTION_RESPONSE_CODE = 'response_code'
    source = None
    products_mapping = {}

    def processor_setup(self, site, source=None):
        self.credentials = StripeIntegration(site)
        self.source = source
        self.site = site
        self.stripe = stripe
        self.query_builder = StripeQueryBuilder()

        if self.credentials.instance:
            self.stripe.api_key = self.credentials.instance.private_key
        elif settings.STRIPE_SECRET_KEY:
            self.stripe.api_key = settings.STRIPE_SECRET_KEY
        else:
            logger.error("StripeProcessor missing keys in settings: STRIPE_PUBLIC_KEY")
            raise ValueError("StripeProcessor missing keys in settings: STRIPE_PUBLIC_KEY")

        # TODO handle this better, but needed to get passed this error message
        # Search is not supported on api version 2016-07-06. Update your API version, or set the API Version of this request to 2020-08-27 or greater.
        # https://stripe.com/docs/libraries/set-version
        self.stripe.api_version = '2022-08-01'

    ##########
    # Stripe utils
    ##########
    def stripe_call(self, *args):
        func, func_args = args
        try:
            if isinstance(func_args, str):
                return func(func_args)

            return func(**func_args)

        except self.stripe.error.CardError as e:
            logger.error(e.user_message)
        except self.stripe.error.RateLimitError as e:
            logger.error(e.user_message)
        except self.stripe.error.InvalidRequestError as e:
            logger.error(e.user_message)
        except self.stripe.error.AuthenticationError as e:
            logger.error(e.user_message)
        except self.stripe.error.APIConnectionError as e:
            logger.error(e.user_message)
        except self.stripe.error.StripeError as e:
            logger.error(e.user_message)
        except Exception as e:
            logger.error(str(e))

        self.transaction_succeded = False

    def convert_decimal_to_integer(self, decimal):
        integer_str_rep = str(decimal).split(".")

        return int("".join(integer_str_rep))



    ##########
    # CRUD Stripe Object
    ##########

    def stripe_create_object(self, stripe_object_class, object_data):
        stripe_object = self.stripe_call(stripe_object_class.create, object_data)

        return stripe_object

    def stripe_query_object(self, stripe_object_class, query):
        if isinstance(query, dict):
            query_data = query
        elif isinstance(query, str):
            query_data = {'query': query}
        else:
            logger.error(f'stripe_query_object: {query} is invalid')
            return None

        query_result = self.stripe_call(stripe_object_class.search, query_data)

        return query_result

    def stripe_delete_object(self, stripe_object_class, object_id):
        delete_result = self.stripe_call(stripe_object_class.delete, object_id)

        return delete_result

    def stripe_get_object(self, stripe_object_class, object_id):
        stripe_object = self.stripe_call(stripe_object_class.retrieve, object_id)

        return stripe_object

    def stripe_update_object(self, stripe_object_class, object_id, object_data):
        object_data['sid'] = object_id
        stripe_object = self.stripe_call(stripe_object_class.modify, object_data)

        return stripe_object

    def stripe_list_objects(self, stripe_object_class, limit=10, starting_after=None):
        object_data = {
            'limit': limit,
            'starting_after': starting_after
        }
        stripe_objects = self.stripe_call(stripe_object_class.list, object_data)

        return stripe_objects




    ##########
    # Stripe Object Builders
    ##########
    def build_customer(self, customer_profile):
        return {
            'name': f"{customer_profile.user.first_name} {customer_profile.user.last_name}",
            'email': customer_profile.user.email,
            'metadata': {'site': customer_profile.site}
        }
    
    def build_product(self, offer):
        return {
            'name': offer.name,
            'metadata': {'site': offer.site.domain, 'pk': offer.pk}

        }

    def build_price(self, offer, price):
        if 'stripe' not in offer.meta or 'product_id' not in offer.meta['stripe']:
            raise TypeError(f"Price cannot be created without a product_id on offer.meta['stripe'] field")

        if isinstance(price, (int, float)):
            currency = DEFAULT_CURRENCY
            unit_amount = self.convert_decimal_to_integer(price)
            is_price_obj = False
        else:
            currency = price.currency
            unit_amount = self.convert_decimal_to_integer(price.cost)
            is_price_obj = True


        price_data = {
            'product': offer.meta['stripe']['product_id'],
            'currency': currency,
            'unit_amount': unit_amount,
            'metadata': {'site': offer.site.domain}
        }

        if is_price_obj:
            price_data['metadata']['pk'] = price.pk
        else:
            price_data['metadata']['msrp'] = price
        
        if offer.terms < TermType.PERPETUAL:
            price_data['recurring'] = {
                'interval': 'month' if offer.term_details['term_units'] == TermDetailUnits.MONTH else 'year',
                'interval_count': offer.term_details['payment_occurrences'],
                'usage_type': 'licensed'
            }
        
        return price_data
    
    def build_coupon(self, offer, price):
        if isinstance(price, (int, float)):
            currency = DEFAULT_CURRENCY
        else:
            currency = price.currency

        coupon_data = {
            'name': offer.name,
            'currency': currency,
            'amount_off': self.convert_decimal_to_integer(offer.discount()),
            'metadata': {'site': offer.site.domain}
        }

        if offer.terms < TermType.PERPETUAL:
            coupon_data['duration']: 'once' if offer.term_details['trial_occurrences'] <= 1 else 'repeating'
            coupon_data['duration_in_months']: offer.get_trial_duration_in_months()
        
        return coupon_data

    def build_payment_method(self):
        return {
            'type': 'card',
            'card': {
                'number': self.payment_info.data.get('card_number'),
                'exp_month': self.payment_info.data.get('expire_month'),
                'exp_year': self.payment_info.data.get('expire_year'),
                'cvc': self.payment_info.data.get('cvv_number'),
            },
            'billing_details': {
                'address': {
                    'line1': self.billing_address.data.get('billing-address_1', None),
                    'line2': self.billing_address.data.get('billing-address_2', None),
                    'city': self.billing_address.data.get("billing-locality", ""),
                    'state': self.billing_address.data.get("billing-state", ""),
                    'country': self.billing_address.data.get("billing-country"),
                    'postal_code': self.billing_address.data.get("billing-postal_code")
                },
                'name': self.payment_info.data.get('full_name', None)
            }
        }

    def build_setup_intent(self, payment_method_id):
        return {
            'customer': self.invoice.profile.meta['stripe_id'],
            'confirm': True,
            'payment_method_types': ['card'],
            'payment_method': payment_method_id,
            'metadata': {'site': self.invoice.site}
        }
    
    def build_subscription(self, subscription, payment_method_id):
        return {
            'customer': self.invoice.profile.meta['stripe_id'],
            'items': [{'price': subscription.meta['stripe']['price_id']}],
            'default_payment_method': payment_method_id,
            'metadata': {'site': self.invoice.site}
        }


    ##########
    # Stripe & Vendor Objects Synchronization
    ##########

    def get_stripe_customers(self, site):
        """
        Returns all Stripe created customers
        """

        clause = self.query_builder.make_clause_template(
            field='metadata',
            key='site',
            value=site.domain,
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Customer, [clause])

        customer_search = self.stripe_query_object(self.stripe.Customer, {'query': query})

        if customer_search:
            return customer_search['data']

        return []

    def get_vendor_customers_in_stripe(self, customer_email_list, site):
        """
        Returns all vendor customers who have been created as Stripe customers
        """
        users = CustomerProfile.objects.filter(
            user__email__iregex=r'(' + '|'.join(customer_email_list) + ')', # iregex used for case insensitive list match
            site=site
        ).select_related('user')

        return users

    def get_vendor_customers_not_in_stripe(self, customer_email_list, site):
        """
        Returns all vendor customers who have not been created as Stripe customers
        """
        users = CustomerProfile.objects.filter(
            site=site
        ).exclude(
            user__email__iregex=r'(' + '|'.join(customer_email_list) + ')',  # iregex used for case insensitive list match
        ).select_related('user')

        return users

    def create_stripe_customers(self, customers):
        for profile in customers:
            profile_data = self.build_customer(profile)
            new_stripe_customer = self.stripe_create_object(self.stripe.Customer, profile_data)
            if new_stripe_customer:
                profile.meta['stripe_id'] = new_stripe_customer['id']
                profile.save()

    def update_stripe_customers(self, customers):
        for profile in customers:
            customer_id = profile.meta.get('stripe_id')
            profile_data = self.build_customer(profile)
            existing_stripe_customer = self.stripe_update_object(self.stripe.Customer, customer_id, profile_data)

            if existing_stripe_customer:
                profile.meta['stripe_id'] = existing_stripe_customer['id']
                profile.save()

    def sync_customers(self, site):
        stripe_customers = self.get_stripe_customers(site)
        stripe_customers_emails = [customer_obj['email'] for customer_obj in stripe_customers]

        vendor_customers_in_stripe = self.get_vendor_customers_in_stripe(stripe_customers_emails, site)

        vendor_customers_with_stripe_meta = vendor_customers_in_stripe.filter(meta__has_key='stripe_id')
        vendor_customers_without_stripe_meta = vendor_customers_in_stripe.exclude(meta__has_key='stripe_id')

        vendor_customers_not_in_stripe = self.get_vendor_customers_not_in_stripe(stripe_customers_emails, site)
        vendor_customer_to_create = vendor_customers_not_in_stripe | vendor_customers_without_stripe_meta

        self.create_stripe_customers(vendor_customer_to_create)
        self.update_stripe_customers(vendor_customers_with_stripe_meta)

    def get_site_offers(self, site):
        """
        Returns all Stripe created Products
        """

        clause = self.query_builder.make_clause_template(
            field='metadata',
            key='site',
            value=site.domain,
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Product, [clause])

        product_search = self.stripe_query_object(self.stripe.Product, {'query': query})

        if product_search:
            return product_search['data']

        return []

    def get_price_with_pk(self, price_pk):
        """
        Returns stripe Price based on metadata pk value
        """

        clause = self.query_builder.make_clause_template(
            field='metadata',
            key='pk',
            value=price_pk,
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Price, [clause])

        price_search = self.stripe_query_object(self.stripe.Price, {'query': query})

        if price_search:
            return price_search['data'][0]

        return None

    def match_coupons(self, coupons, offer):
        matches = []
        amount_off = self.convert_decimal_to_integer(offer.discount())
        duration = offer.get_trial_duration_in_months()
        for coupon in coupons:
            if coupon['metadata']['site'] == offer.site.domain and coupon['amount_off'] == amount_off\
                    and coupon['duration_in_months'] == duration:
                matches.append(coupon)
        return matches

    def get_coupons(self):
        """
        Returns all stripe Coupons

        This is needed since there is no search method on Coupon. Will make multiple stripe calls until the
        list is exhausted
        """
        coupons_list = []
        starting_after = None
        while True:
            coupons = self.stripe_list_objects(self.stripe.Coupon, limit=100, starting_after=starting_after)
            coupons_list.extend(coupons)
            if coupons['has_more']:
                starting_after = coupons['data'][-1]['id']
            else:
                break

        return coupons_list

    def get_vendor_offers_in_stripe(self, offer_pk_list, site):
        offers = Offer.objects.filter(site=site, pk__in=offer_pk_list)
        return offers

    def get_vendor_offers_not_in_stripe(self, offer_pk_list, site):
        offers = Offer.objects.filter(site=site).exclude(pk__in=offer_pk_list)
        return offers

    def create_offers(self, offers):
        for offer in offers:
            # build product first, since product_id is needed to build price later
            product_data = self.build_product(offer)

            new_stripe_product = self.stripe_create_object(self.stripe.Product, product_data)

            if new_stripe_product:
                if offer.meta.get('stripe'):
                    offer.meta['stripe']['product_id'] = new_stripe_product['id']
                else:
                    offer.meta['stripe'] = {'product_id': new_stripe_product['id']}

            price_data = self.build_price(offer, offer.current_price_object())
            coupon_data = self.build_coupon(offer, offer.current_price_object())

            new_stripe_price = self.stripe_create_object(self.stripe.Price, price_data)
            new_stripe_coupon = self.stripe_create_object(self.stripe.Coupon, coupon_data)

            if new_stripe_price:
                if offer.meta.get('stripe'):
                    offer.meta['stripe']['price_id'] = new_stripe_price['id']
                else:
                    offer.meta['stripe'] = {'price_id': new_stripe_price['id']}

            if new_stripe_coupon:
                if offer.meta.get('stripe'):
                    offer.meta['stripe']['coupon_id'] = new_stripe_coupon['id']
                else:
                    offer.meta['stripe'] = {'coupon_id': new_stripe_coupon['id']}

            offer.save()


    def update_offers(self, offers):
        coupons = self.get_coupons()

        for offer in offers:

            # Handle product
            product_id = offer.meta['stripe']['product_id']
            product_data = self.build_product(offer)
            existing_stripe_product = self.stripe_update_object(self.stripe.Product, product_id, product_data)
            if existing_stripe_product:
                if offer.meta.get('stripe'):
                    offer.meta['stripe']['product_id'] = existing_stripe_product['id']
                else:
                    offer.meta['stripe'] = {'product_id': existing_stripe_product['id']}

            # Handle Price
            price = offer.current_price_object()
            price_data = self.build_price(offer, price)
            stripe_price_obj = self.get_price_with_pk(price.pk)

            if stripe_price_obj:
                stripe_price = self.stripe_update_object(self.stripe.Price, stripe_price_obj['id'], price_data)
            else:
                stripe_price = self.stripe_create_object(self.stripe.Price, price_data)

            if offer.meta.get('stripe'):
                offer.meta['stripe']['price_id'] = stripe_price['id']
            else:
                offer.meta['stripe'] = {'price_id': stripe_price['id']}

            # Handle Coupon
            coupon_data = self.build_coupon(offer, price)
            discount = self.convert_decimal_to_integer(offer.discount())
            trial_days = offer.term_details.get('trial_days', 0)

            # If this offer has a discount check if its on stripe to create, update, delete
            if discount or trial_days:
                stripe_coupon_matches = self.match_coupons(coupons, offer)
                if not stripe_coupon_matches:
                    stripe_coupon = self.stripe_create_object(self.stripe.Coupon, coupon_data)
                elif len(stripe_coupon_matches) == 1:
                    coupon_id = stripe_coupon_matches[0]['id']
                    stripe_coupon = self.stripe_update_object(self.stripe.Coupon, coupon_id, coupon_data)
                else:
                    # Duplicates, so delete all but one and update it
                    for coupon_data in stripe_coupon_matches[1:]:
                        self.stripe_delete_object(self.stripe.Coupon, coupon_data['id'])

                    # update the only one we have remaining
                    stripe_coupon = self.stripe_update_object(self.stripe.Coupon, stripe_coupon_matches[0]['id'], coupon_data)


                if offer.meta.get('stripe'):
                    offer.meta['stripe']['coupon_id'] = stripe_coupon['id']
                else:
                    offer.meta['stripe'] = {'coupon_id': stripe_coupon['id']}

            offer.save()

    def sync_offers(self, site):
        products = self.get_site_offers(site)
        offer_pk_list = [product['metadata']['pk'] for product in products]

        offers_in_vendor = self.get_vendor_offers_in_stripe(offer_pk_list, site)

        offers_in_vendor_with_stripe_meta = offers_in_vendor.filter(meta__has_key='stripe')
        offers_in_vendor_without_stripe_meta = offers_in_vendor.exclude(meta__has_key='stripe')
        
        offers_not_in_vendor = self.get_vendor_offers_not_in_stripe(offer_pk_list, site)
        offers_to_create = offers_not_in_vendor | offers_in_vendor_without_stripe_meta

        self.create_offers(offers_to_create)
        self.update_offers(offers_in_vendor_with_stripe_meta)

    def sync_stripe_vendor_objects(self, site):
        """
        Sync up all the CustomerProfiles, Offers, Prices, and Coupons for all of the sites
        """

        self.sync_customers(site)
        self.sync_offers(site)

    def create_setup_intent(self, setup_intent_data):
        setup_intent = self.stripe_create_object(self.stripe.SetupIntent, setup_intent_data)

        return setup_intent

    def create_payment_intent(self, payment_intent_data):
        # Will return client secret value to be returned to the front end to continue processing payment

        #intent = self.stripe_call(self.stripe.PaymentIntent.create, {
        #    'customer': customer['id'],
        #    'setup_future_usage': 'off_session',
        #    'amount': self.invoice.get_one_time_transaction_total(),
        #    'currency': self.invoice.currency,
        #    'automatic_payment_methods': {
        #        'enabled': True
        #    }
        #})

        payment_intent = self.stripe_create_object(self.stripe.PaymentIntent, payment_intent_data)

        return payment_intent

    def set_stripe_payment_source(self):
        """
        This is needed for the charge api due to this error message:
        'You cannot create a charge with a PaymentMethod. Use the Payment Intents API instead'
        """
        if not self.source:
            if self.payment_info.is_valid():
                card_number = self.payment_info.cleaned_data.get('card_number')
                exp_month = self.payment_info.cleaned_data.get('expire_month')
                exp_year = self.payment_info.cleaned_data.get('expire_year')
                cvc = self.payment_info.cleaned_data.get('cvc_number')
                card = {
                    'number': card_number,
                    'exp_month': exp_month,
                    'exp_year': exp_year,
                    'cvc': cvc
                 }
                card = self.stripe_create_object(self.stripe.Token, {'card':card})
                if card:
                    self.source = card['id']

    def create_payment_method(self, payment_method_data):
        payment_method = self.stripe_create_object(self.stripe.PaymentMethod, payment_method_data)

        return payment_method

    def does_product_exist(self, name, metadata):
        name_clause = self.query_builder.make_clause_template(
            field='name',
            value=name,
            operator=self.query_builder.EXACT_MATCH,
            next_operator=self.query_builder.AND
        )

        metadata_clause = self.query_builder.make_clause_template(
            field='metadata',
            key=metadata['key'],
            value=metadata['value'],
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Product, [name_clause, metadata_clause])

        search_data = self.stripe_query_object(self.stripe.Product, {'query': query})
        if search_data:
            if search_data.get('data', False):
                return True
        return False

    def does_price_exist(self, product, metadata):
        product_clause = self.query_builder.make_clause_template(
            field='product',
            value=product,
            operator=self.query_builder.EXACT_MATCH,
            next_operator=self.query_builder.AND
        )
        metadata_clause = self.query_builder.make_clause_template(
            field='metadata',
            key=metadata['key'],
            value=metadata['value'],
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Price, [product_clause, metadata_clause])

        search_data = self.stripe_query_object(self.stripe.Price, {'query': query})

        if search_data:
            if search_data.get('data', False):
                return True
        return False

    def initialize_products(self, site):
        """
        Grab all subscription offers on invoice and either create or fetch Stripe products.
        Then using those products, create Stripe prices. Add all that to products_mapping

        Will be used in create_subscription
        """
        # Create Customer loop through all site customer and save their id's
        # Create Stripe product with site offers
        ## Create Stripe Price from Offer.Prices
        ## Create Coupons from Offer.term_details. 
        for subscription in self.invoice.get_recurring_order_items():
            product_name = subscription.offer.name
            product_name_full = f'{product_name} - site {self.site.domain}'
            product_details = subscription.offer.term_details
            total = self.to_valid_decimal(subscription.total - subscription.discounts)
            interval = "month" if product_details['term_units'] == TermDetailUnits.MONTH else "year"
            metadata = {
                'key': 'site',
                'value': 'site4',
                'field': 'metadata'
            }
            product_response = self.does_product_exist(product_name_full, metadata=metadata)
            if product_response:
                product_id = self.get_product_id_with_name(product_name_full)

                # Each product needs an attached price obj. Check if one exists for the product
                # and attach it to the mapping or create one and attach
                if product_id:
                    price_response = self.does_price_exist(product_id)
                    if price_response:
                        price_id = self.get_price_id_with_product(product_id)
                    else:
                        price_id = self.create_price_with_product(product_id)

                    self.products_mapping[product_name] = {
                        'product_id': product_id,
                        'price_id': price_id
                    }

            else:
                # product doesnt exist, create it and related pricing obj
                product = self.stripe_call(self.stripe.Product.create, {
                    'name': product_name,
                    'metadata': product_details,
                    'default_price_data': {
                        'currency': self.invoice.currency,
                        'unit_amount_decimal': total,
                        'recurring': {
                            'interval': interval,
                            'interval_count': subscription.offer.get_payment_occurrences()
                        }
                    }
                })
                if product:
                    product_id = product['id']

                    # Each product needs an attached price obj. Check if one exists for the product
                    # and attach it to the mapping or create one and attach
                    price_response = self.does_price_exist(product_id)
                    if price_response:
                        price_id = self.get_price_id_with_product(product_id)
                    else:
                        price_id = self.create_price_with_product(product_id)

                    self.products_mapping[product_name] = {
                        'product_id': product_id,
                        'price_id': price_id
                    }

    def get_product_id_with_name(self, name, metadata):
        name_clause = self.query_builder.make_clause_template(
            field='name',
            value=name,
            operator=self.query_builder.EXACT_MATCH,
            next_operator=self.query_builder.AND
        )
        metadata_clause = self.query_builder.make_clause_template(
            field='metadata',
            key=metadata['key'],
            value=metadata['value'],
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Product, [name_clause, metadata_clause])
        search_data = self.stripe_query_object(self.stripe.Product, {'query': query})

        if search_data:
            return search_data['data'][0]['id']
        return None

    def get_price_id_with_product(self, product):
        price = self.stripe_get_object(self.stripe.Price, {'id': product})
        if price:
            return price['id']
        return None

    def create_price_with_product(self, product):
        price_data = {
            'currency': self.invoice.currency,
            'product': product
        }
        price = self.stripe_create_object(self.stripe.Price, price_data)
        if price:
            return price['id']
        return None

    def create_charge(self):
        charge_data = {
            'amount': self.to_stripe_valid_unit(self.invoice.get_one_time_transaction_total()),
            'currency': self.invoice.currency,
            'source': self.source,
        }
        charge = self.stripe_create_object(self.stripe.Charge, charge_data)
        if charge:
            return charge
        return None

    def parse_response(self, subscription=True):
        """
        Processes the transaction response
        """
        transaction_id = ''
        raw_data = ''
        messages = ''
        
        if not subscription:
            transaction_id = self.charge['id']
            raw_data = str(self.charge)
            messages = f'trans id is {transaction_id}'
        else:
            if self.stripe_subscription.get('id'):
                transaction_id = self.stripe_subscription['id']
                raw_data = str(self.stripe_subscription)
                messages = f'trans id is {transaction_id}'

        self.transaction_id = transaction_id
        self.transaction_response = self.make_transaction_response(
            raw=raw_data,
            messages=messages
        )

    def parse_success(self, subscription=True):
        if not subscription:
            if self.charge.get('id'):
                self.transaction_succeded = True
        else:
            if self.stripe_subscription.get('id'):
                self.transaction_succeded = True

    ##########
    # Base Processor Transaction Implementations
    ##########
    def pre_authorization(self):
        """
        Called before the authorization begins.
        """
        pass

    def process_payment(self):
        self.transaction_succeded = False
        self.charge = self.create_charge()
        
        if self.charge and self.charge["captured"]:
            self.transaction_succeded = True
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = '201'
            self.transaction_message[self.TRANSACTION_SUCCESS_MESSAGE] = "Success"
            self.payment.status = PurchaseStatus.CAPTURED
            self.payment.save()
            self.update_invoice_status(InvoiceStatus.COMPLETE)
            self.parse_response(subscription=False)

    def subscription_payment(self, subscription):
        payment_method_data = self.build_payment_method()
        stripe_payment_method = self.stripe_create_object(self.stripe.PaymentMethod, payment_method_data)
        
        setup_intent_object = self.build_setup_intent(stripe_payment_method.id)
        stripe_setup_intent = self.stripe_create_object(self.stripe.SetupIntent, setup_intent_object)

        subscription_obj = self.build_subscription(subscription, stripe_payment_method.id)
        self.stripe_subscription = self.processor.stripe_create_object(self.processor.stripe.Subscription, subscription_obj)

        self.parse_response()
        self.parse_success()

        if self.invoice.vendor_notes is None:
            self.invoice.vendor_notes = {}

        self.invoice.vendor_notes['stripe_id'] = self.transaction_info['transaction_id']
        self.invoice.save()
        



