"""
Payment processor for Stripe.
"""
import django.dispatch
import json
import logging
import stripe
import uuid

from math import modf
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import timezone
from vendor.config import DEFAULT_CURRENCY
from vendor.integrations import StripeIntegration
from vendor.models import Offer, CustomerProfile
from vendor.models.choice import (
    Country,
    SubscriptionStatus,
    TransactionTypes,
    PaymentTypes,
    TermType,
    TermDetailUnits,
    InvoiceStatus,
    PurchaseStatus
)
from vendor.processors.base import PaymentProcessorBase


logger = logging.getLogger(__name__)

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


    def customer_setup(self):
        if not self.invoice.profile.meta.get('stripe_id'):
            self.create_stripe_customers([self.invoice.profile])
        
        stripe_customer = self.stripe_get_object(self.stripe.Customer, self.invoice.profile.meta.get('stripe_id'))

        if not stripe_customer:
            self.create_stripe_customers([self.invoice.profile])

    def subscription_offer_setup(self):
        offers_to_sync = []
        for order_item in self.invoice.order_items.all():
            if not order_item.offer.meta.get('stripe_id'):
                offers_to_sync.append(order_item.offer)

        self.create_offers(offers_to_sync)

    ##########
    # Parsers
    ##########
    def parse_response(self, response_data):
        """
        Processes the transaction response
        """
        ...


    ##########
    # Stripe utils
    ##########
    def stripe_call(self, *args):
        func, func_args = args
        self.transaction_succeeded = False

        try:
            if isinstance(func_args, str):
                self.transaction_response = func(func_args)
            else:
                self.transaction_response = func(**func_args)

        except (self.stripe.error.CardError, self.stripe.error.RateLimitError,
                self.stripe.error.InvalidRequestError, self.stripe.error.AuthenticationError,
                self.stripe.error.APIConnectionError, self.stripe.error.StripeError,
                Exception) as e:

            user_message = ""
            if hasattr(e, 'user_message'):
                user_message = e.user_message
            raw = {
                'exception': f"{e}\n{func}\n{func_args}:user_message: {user_message}"
            }
            errors = {
                'error': f"{e}"
            }
            self.transaction_info = self.get_transaction_info(raw=raw, errors=errors)
            logger.error(self.transaction_info)
            return None

        self.transaction_succeeded = True
        self.transaction_info = self.get_transaction_info(raw=f"{func} - {func_args} {json.dumps(self.transaction_response)}", data=self.transaction_response.data if 'data' in self.transaction_response else "")

        return self.transaction_response

    def convert_decimal_to_integer(self, decimal):
        if decimal == 0:
            return 0
            
        fraction_part, whole_part = modf(decimal)
                
        whole_str = str(whole_part).split('.')[0]
        fraction_str = str(fraction_part).split('.')[1][:2]

        if len(fraction_str) < 2:
            fraction_str = "0" + fraction_str

        stripe_amount = int("".join([whole_str, fraction_str]))
            
        return stripe_amount

    ##########
    # CRUD Stripe Object
    ##########

    def stripe_create_object(self, stripe_object_class, object_data):
        stripe_object = self.stripe_call(stripe_object_class.create, object_data)

        return stripe_object

    def stripe_query_object(self, stripe_object_class, query, limit=100, page=None):
        if isinstance(query, dict):
            query_data = query
            query_data['limit'] = limit
            query_data['page'] = page

        elif isinstance(query, str):
            query_data = {
                'query': query,
                'limit': limit,
                'page': page
            }

        else:
            logger.error(f'stripe_query_object: {query} is invalid')
            return None

        query_result = self.stripe_call(stripe_object_class.search, query_data)

        return query_result

    def stripe_delete_object(self, stripe_object_class, object_id):
        delete_result = self.stripe_call(stripe_object_class.delete, object_id)

        return delete_result

    def stripe_get_object(self, stripe_object_class, object_id, expand=None):
        if expand:
            # some fields are expandable https://stripe.com/docs/api/expanding_objects
            object_id = {
                'id': object_id,
                'expand': expand
            }
        stripe_object = self.stripe_call(stripe_object_class.retrieve, object_id)

        return stripe_object

    def stripe_update_object(self, stripe_object_class, object_id, object_data):
        object_data['sid'] = object_id
        stripe_object = self.stripe_call(stripe_object_class.modify, object_data)

        if self.transaction_succeeded:
            self.transaction_succeeded = False
            return stripe_object

        return None

    def stripe_list_objects(self, stripe_object_class, limit=100, starting_after=None):
        object_data = {
            'limit': limit,
            'starting_after': starting_after
        }
        stripe_objects = self.stripe_call(stripe_object_class.list, object_data)

        return stripe_objects

    def get_all_stripe_list_objects(self, stripe_object):
        """
        Get entire list of any stripe object with .list() method.
        Will make multiple stripe calls until the list is exhausted
        """
        object_list = []
        starting_after = None
        while True:
            objs = self.stripe_list_objects(stripe_object, limit=100, starting_after=starting_after)
            object_list.extend(objs)
            if objs['has_more']:
                starting_after = objs['data'][-1]['id']
            else:
                break

        return object_list

    def get_all_stripe_search_objects(self, stripe_object, query, limit=100):
        """
        Get entire list of any stripe object with .search() method.
        Will make multiple stripe calls until the list is exhausted
        """
        object_list = []
        page = None

        while True:
            objs = self.stripe_query_object(stripe_object, query=query, limit=limit, page=page)
            object_list.extend(objs['data'])
            if objs['has_more']:
                page = objs['next_page']
            else:
                break

        return object_list
        
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
    # TODO: Try to reduce the number of arguments to max 3. 
    def build_price(self, offer, mspr, current_price, currency, price_pk=None):
        if 'stripe' not in offer.meta or 'product_id' not in offer.meta['stripe']:
            raise TypeError(f"Price cannot be created without a product_id on offer.meta['stripe'] field")

        price_data = {
            'active': True,
            'product': offer.meta['stripe']['product_id'],
            'currency': currency,
            'unit_amount': self.convert_decimal_to_integer(current_price),
            'metadata': {
                'site': offer.site.domain,
                'msrp': mspr
                }
        }

        if price_pk:
            price_data['metadata']['pk'] = price_pk
        
        if offer.terms < TermType.PERPETUAL:
            price_data['recurring'] = {
                'interval': 'month' if offer.term_details['term_units'] == TermDetailUnits.MONTH else 'year',
                'interval_count': offer.term_details['period_length'],
                'usage_type': 'licensed'
            }
        
        return price_data
    
    def is_card_valid(self):
        # TODO: see how stripe has check for 
        return True

    def build_coupon(self, offer, currency):
        coupon_data = {
            'name': offer.name,
            'currency': currency,
            'amount_off': self.convert_decimal_to_integer(offer.discount(currency)),
            'metadata': {'site': offer.site.domain}
        }

        if offer.terms < TermType.PERPETUAL:
            coupon_data['amount_off'] = self.convert_decimal_to_integer(offer.get_trial_discount())
            coupon_data['duration'] = 'once' if offer.term_details['trial_occurrences'] <= 1 else 'repeating'
            coupon_data['duration_in_months'] = offer.term_details['trial_occurrences']
        
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
                    'country': Country.names[Country.values.index(int(self.billing_address.data.get("billing-country")))],
                    'postal_code': self.billing_address.data.get("billing-postal_code")
                },
                'name': self.payment_info.data.get('full_name', None),
                'email': self.invoice.profile.user.email
            }
        }

    def build_payment_intent(self, amount, currency=DEFAULT_CURRENCY):
        return {
            'amount': amount,
            'currency': currency
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
            'coupon': subscription.offer.meta['stripe'].get('coupon_id'),
            'items': [{'price': subscription.offer.meta['stripe']['price_id']}],
            'default_payment_method': payment_method_id,
            'metadata': {'site': self.invoice.site},
            'trial_period_days': subscription.offer.get_trial_days()

        }

    def build_invoice_line_item(self, order_item, invoice_id):
        line_item = {
            'customer': self.invoice.profile.meta.get('stripe_id'),
            'invoice': invoice_id,
            'price': order_item.offer.meta['stripe'].get('price_id'),
        }

        if order_item.offer.has_any_discount_or_trial():
            line_item['discounts'] = [{'coupon': order_item.offer.meta['stripe'].get('coupon_id')}]

        return line_item

    def build_invoice(self, currency=DEFAULT_CURRENCY):
        return {
            'customer': self.invoice.profile.meta.get('stripe_id'),
            'currency': currency,
        }

    ##########
    # Customers
    ##########

    def get_stripe_customers(self, site, expand=None):
        """
        Returns all Stripe created customers for this site
        """

        clause = self.query_builder.make_clause_template(
            field='metadata',
            key='site',
            value=site.domain,
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Customer, [clause])

        customer_search = self.get_all_stripe_search_objects(self.stripe.Customer, {'query': query})

        return customer_search

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
                profile_meta = profile.meta
                profile_meta['stripe_id'] = new_stripe_customer['id']
                CustomerProfile.objects.filter(pk=profile.pk).update(meta=profile_meta)

    def update_stripe_customers(self, customers):
        for profile in customers:
            customer_id = profile.meta.get('stripe_id')
            profile_data = self.build_customer(profile)
            existing_stripe_customer = self.stripe_update_object(self.stripe.Customer, customer_id, profile_data)

            if existing_stripe_customer:
                profile_meta = profile.meta
                profile_meta['stripe_id'] = existing_stripe_customer['id']
                CustomerProfile.objects.filter(pk=profile.pk).update(meta=profile_meta)
            else:
                self.create_stripe_customers([profile])
    ##########
    # Offers/Products
    ##########
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

        product_search = self.get_all_stripe_search_objects(self.stripe.Product, {'query': query})

        return product_search

    def get_vendor_offers_in_stripe(self, offer_pk_list, site):
        offers = Offer.objects.filter(site=site, pk__in=offer_pk_list)
        return offers

    def get_vendor_offers_not_in_stripe(self, offer_pk_list, site):
        offers = Offer.objects.filter(site=site).exclude(pk__in=offer_pk_list)
        return offers

    def create_offers(self, offers):
        for offer in offers:
            offer_meta = offer.meta
            # build product first, since product_id is needed to build price later
            product_data = self.build_product(offer)

            new_stripe_product = self.stripe_create_object(self.stripe.Product, product_data)

            if new_stripe_product:
                if offer_meta.get('stripe'):
                    offer_meta['stripe']['product_id'] = new_stripe_product['id']
                else:
                    offer_meta['stripe'] = {'product_id': new_stripe_product['id']}

            # TODO: Need to explore what is the best way to upload prices in each currency
            # currently we will only support the default currency (DEFAULT_CURRENCY) se
            # on the vendor.config.py file
            # for currency in AVAILABLE_CURRENCIES:
            #     ...
            price = offer.get_current_price_instance() if offer.get_current_price_instance() else None
            msrp = offer.get_msrp()
            current_price = msrp
            price_pk = None
            
            if price:
                if not msrp and price.cost > msrp:
                    current_price = price.cost
                price_pk = price.pk

            price_data = self.build_price(offer, msrp, current_price, DEFAULT_CURRENCY, price_pk)
            new_stripe_price = self.stripe_create_object(self.stripe.Price, price_data)
            
            if new_stripe_price:
                if offer_meta.get('stripe'):
                    offer_meta['stripe']['price_id'] = new_stripe_price['id']
                else:
                    offer_meta['stripe'] = {'price_id': new_stripe_price['id']}

            if offer.discount() or offer.get_trial_amount():
                coupon_data = self.build_coupon(offer, DEFAULT_CURRENCY)

                new_stripe_coupon = self.stripe_create_object(self.stripe.Coupon, coupon_data)

                if new_stripe_coupon:
                    if offer_meta.get('stripe'):
                        offer_meta['stripe']['coupon_id'] = new_stripe_coupon['id']
                    else:
                        offer_meta['stripe'] = {'coupon_id': new_stripe_coupon['id']}
            
            Offer.objects.filter(pk=offer.pk).update(meta=offer_meta)  # Doing an update to avoid triggering post_save()

    def update_offers(self, offers):
        coupons = self.get_coupons()

        for offer in offers:
            # Handle product
            offer_meta = offer.meta
            product_id = offer.meta['stripe']['product_id']
            product_data = self.build_product(offer)
            existing_stripe_product = self.stripe_update_object(self.stripe.Product, product_id, product_data)
            
            if not existing_stripe_product:
                self.create_offers([offer])
            else:
                if offer_meta.get('stripe'):
                    offer_meta['stripe']['product_id'] = existing_stripe_product['id']
                else:
                    offer_meta['stripe'] = {'product_id': existing_stripe_product['id']}

                # Handle Price
                # TODO: Need to explore what is the best way to upload prices in each currency
                # currently we will only support the default currency (DEFAULT_CURRENCY) se
                # on the vendor.config.py file
                # for currency in AVAILABLE_CURRENCIES:
                #     ...
                msrp = offer.get_msrp()
                stripe_product_prices = self.get_stripe_prices_for_product(product_id)

                price = offer.get_current_price_instance() if offer.get_current_price_instance() else None
                current_price = msrp
                price_pk = None
                
                if price:
                    current_price = price.cost
                    price_pk = price.pk
                
                price_data = self.build_price(offer, msrp, current_price, DEFAULT_CURRENCY, price_pk)
                stripe_price = None

                if not stripe_product_prices:
                    stripe_price = self.stripe_create_object(self.stripe.Price, price_data)

                else:
                    prices_to_deactivate = [stripe_price for stripe_price in stripe_product_prices if self.convert_decimal_to_integer(current_price) != stripe_price.unit_amount]
                    prices_to_check = [stripe_price for stripe_price in stripe_product_prices if self.convert_decimal_to_integer(current_price) == stripe_price.unit_amount]
                    
                    for stripe_price_deactivate in prices_to_deactivate:
                        self.stripe_update_object(self.stripe.Price, stripe_price_deactivate.id, {'active': False})
                    
                    any_match = False
                    for stripe_price_check in prices_to_check:
                        if self.does_stripe_and_vendor_price_match(stripe_price_check, price_data):
                            any_match = True
                            stripe_price = stripe_price_check
                        else:
                            self.stripe_update_object(self.stripe.Price, stripe_price_check.id, {'active': False})
                    
                    if not any_match:
                        stripe_price = self.stripe_create_object(self.stripe.Price, price_data)

                if stripe_price:
                    if offer_meta.get('stripe'):
                        offer_meta['stripe']['price_id'] = stripe_price['id']
                    else:
                        offer_meta['stripe'] = {'price_id': stripe_price['id']}

                # Handle Coupon
                coupon_data = self.build_coupon(offer, DEFAULT_CURRENCY)
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

                    if stripe_coupon:
                        if offer_meta.get('stripe'):
                            offer_meta['stripe']['coupon_id'] = stripe_coupon['id']
                        else:
                            offer_meta['stripe'] = {'coupon_id': stripe_coupon['id']}

                Offer.objects.filter(pk=offer.pk).update(meta=offer_meta)

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

    ##########
    # Prices
    ##########
    def does_stripe_and_vendor_price_match(self, stripe_price, vendor_price):
        if not stripe_price.unit_amount == vendor_price['unit_amount']:
            return False
        
        if 'recurring' in vendor_price:
            if 'recurring' not in stripe_price:
                return False

            if not stripe_price.recurring['interval'] == vendor_price['recurring']['interval']:
                return False
            
            if not stripe_price.recurring['interval_count'] == vendor_price['recurring']['interval_count']:
                return False
        
        return True

    def get_price_id_with_product(self, product):
        price = self.stripe_get_object(self.stripe.Price, {'id': product})

        if price:
            return price['id']

        return None
    
    def get_stripe_prices_for_product(self, product):
        product_clause = self.query_builder.make_clause_template(
            field='product',
            value=product,
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Price, [product_clause])

        search_data = self.get_all_stripe_search_objects(self.stripe.Price, {'query': query})

        return search_data

    def get_customer_email(self, customer_id):
        customer = self.stripe_get_object(self.stripe.Customer, customer_id)

        if customer:
            return customer['email']
        return None

    def get_customer_id_for_expiring_cards(self, month):
        # month is passed as YYYY-M

        customers = self.get_stripe_customers(self.site)
        sources = [
            (customer['id'], customer['email'], customer['default_source'])
            for customer in customers if customer.get('default_source')
        ]

        expired_cards_emails = []
        for customer_id, customer_email, source_id in sources:
            if 'card' in source_id:
                stripe_card = self.stripe_call(
                    self.stripe.Customer.retrieve_source,
                    {'id': customer_id, 'nested_id': source_id}
                )
                if stripe_card:
                    if stripe_card['exp_year'] and stripe_card['exp_month']:
                        exp_date = f"{stripe_card['exp_year']}-{stripe_card['exp_month']}"
                        exp_date_obj = timezone.datetime.strptime(exp_date, "%Y-%m")
                        current_date_obj = timezone.datetime.strptime(month, "%Y-%m")
                        date_diff = (exp_date_obj - current_date_obj).days
                        if 0 < date_diff <= 60:
                            expired_cards_emails.append(customer_email)

        return expired_cards_emails

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

    def create_price_with_product(self, product):
        price_data = {
            'currency': self.invoice.currency,
            'product': product
        }

        price = self.stripe_create_object(self.stripe.Price, price_data)

        if price:
            return price['id']

        return None

    ##########
    # Coupons
    ##########
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

        This is needed since there is no search method on Coupon.
        """

        return self.get_all_stripe_list_objects(self.stripe.Coupon) or []

    ##########
    # Sync Vendor and Stripe
    ##########
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
                            'interval_count': subscription.offer.get_period_length()
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

    def sync_customers(self, site):
        logger.info(f"StripeProcessor sync_customers Started")
        stripe_customers = self.get_stripe_customers(site)
        stripe_customers_emails = [customer_obj['email'] for customer_obj in stripe_customers]

        vendor_customers_in_stripe = self.get_vendor_customers_in_stripe(stripe_customers_emails, site)

        vendor_customers_with_stripe_meta = vendor_customers_in_stripe.filter(meta__has_key='stripe_id')
        vendor_customers_without_stripe_meta = vendor_customers_in_stripe.exclude(meta__has_key='stripe_id')

        vendor_customers_not_in_stripe = self.get_vendor_customers_not_in_stripe(stripe_customers_emails, site)
        vendor_customer_to_create = vendor_customers_not_in_stripe | vendor_customers_without_stripe_meta

        self.create_stripe_customers(vendor_customer_to_create)
        self.update_stripe_customers(vendor_customers_with_stripe_meta)
        logger.info(f"StripeProcessor sync_customers Finished")

    def sync_offers(self, site):
        logger.info(f"StripeProcessor sync_offers Started")
        products = self.get_site_offers(site)
        offer_pk_list = [product['metadata']['pk'] for product in products]

        offers_in_vendor = self.get_vendor_offers_in_stripe(offer_pk_list, site)

        offers_in_vendor_with_stripe_meta = offers_in_vendor.filter(meta__has_key='stripe')
        offers_in_vendor_without_stripe_meta = offers_in_vendor.exclude(meta__has_key='stripe')
        
        offers_not_in_vendor = self.get_vendor_offers_not_in_stripe(offer_pk_list, site)
        offers_to_create = offers_not_in_vendor | offers_in_vendor_without_stripe_meta

        self.create_offers(offers_to_create)
        self.update_offers(offers_in_vendor_with_stripe_meta)
        logger.info(f"StripeProcessor sync_offers Finished")

    def sync_stripe_vendor_objects(self, site):
        """
        Sync up all the CustomerProfiles, Offers, Prices, and Coupons for all of the sites
        """
        logger.info(f"StripeProcessor sync_stripe_vendor_objects Started")
        self.sync_customers(site)
        self.sync_offers(site)
        logger.info(f"StripeProcessor sync_stripe_vendor_objects Finished")

    ##########
    # Stripe Transactions
    ##########
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

    ##########
    # Base Processor Transaction Implementations
    ##########
    def pre_authorization(self):
        """
        Called before the authorization begins.
        """
        self.customer_setup()
        self.subscription_offer_setup()
        self.transaction_succeeded = False

    def process_payment(self):
        invoice_data = self.build_invoice()
        stripe_invoice = self.stripe_create_object(self.stripe.Invoice, invoice_data)
        if not stripe_invoice:
            return None

        payment_method_data = self.build_payment_method()
        stripe_payment_method = self.stripe_create_object(self.stripe.PaymentMethod, payment_method_data)
        if not stripe_payment_method:
            return None

        self.stripe_call(stripe_payment_method.attach, {'customer': self.invoice.profile.meta.get('stripe_id')})
        if not self.transaction_succeeded:
            return None
        
        stripe_invoice
        self.invoice.vendor_notes['stripe_id'] = stripe_invoice.id
        self.invoice.save()
        
        stripe_line_items = []
        for order_item in self.invoice.get_one_time_transaction_order_items():
            line_item_data = self.build_invoice_line_item(order_item, stripe_invoice.id)
            stripe_line_item = self.stripe_create_object(self.stripe.InvoiceItem, line_item_data) 
            stripe_line_items.append(stripe_line_item)
        
        stripe_invoice.lines = stripe_line_items

        amount = self.convert_decimal_to_integer(self.invoice.get_one_time_transaction_total())
        payment_intent_data = self.build_payment_intent(amount)
        stripe_payment_intent = self.stripe_create_object(self.stripe.PaymentIntent, payment_intent_data)

        if not stripe_payment_intent:
            return None

        self.stripe_call(stripe_invoice.pay, {"payment_method": stripe_payment_method.id})

        if self.transaction_succeeded:
            self.transaction_id = stripe_invoice.payment_intent

    def subscription_payment(self, subscription):
        payment_method_data = self.build_payment_method()
        stripe_payment_method = self.stripe_create_object(self.stripe.PaymentMethod, payment_method_data)
        if not stripe_payment_method:
            return None

        setup_intent_object = self.build_setup_intent(stripe_payment_method.id)
        if not setup_intent_object:
            return None

        stripe_setup_intent = self.stripe_create_object(self.stripe.SetupIntent, setup_intent_object)
        if not stripe_setup_intent:
            return None

        subscription_obj = self.build_subscription(subscription, stripe_payment_method.id)        
        stripe_subscription = self.stripe_create_object(self.stripe.Subscription, subscription_obj)
        
        if not stripe_subscription or stripe_subscription.status == 'incomplete':
            self.transaction_succeeded = False
            self.transaction_info['errors'] = "Subscription was not settled"
            return None

        if self.invoice.vendor_notes is None:
            self.invoice.vendor_notes = {}

        self.invoice.vendor_notes['stripe_id'] = stripe_subscription.latest_invoice
        self.invoice.save()

        self.subscription_id = stripe_subscription.id

