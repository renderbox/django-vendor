import json
import logging
from decimal import Decimal, ROUND_UP
from math import modf

import stripe
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models
from django.utils import timezone

from vendor.config import DEFAULT_CURRENCY, StripeConnectAccountConfig, VendorSiteCommissionConfig, STRIPE_BASE_COMMISSION, STRIPE_RECURRING_COMMISSION
from vendor.integrations import StripeIntegration
from vendor.models import (CustomerProfile, Invoice, Offer, Payment, Receipt,
                           Subscription)
from vendor.models.choice import (Country, InvoiceStatus, PurchaseStatus,
                                  SubscriptionStatus, TermDetailUnits,
                                  TermType)
from vendor.processors.base import PaymentProcessorBase

logger = logging.getLogger(__name__)


class PRORATION_BEHAVIOUR_CHOICE(models.TextChoices):
    ALWAYS_INVOICE    = "always_invoice", "Always Invoice"
    CREATE_PRORATIONS = "create_proration", "Create Proration"
    NONE              = "none", "None"


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
        self.stripe.api_version = '2023-08-16'

    def validate_invoice_customer_in_stripe(self):
        if not self.invoice.profile.meta.get('stripe_id'):
            self.create_stripe_customers([self.invoice.profile])
        
        stripe_customer = self.stripe_get_object(self.stripe.Customer, self.invoice.profile.meta.get('stripe_id'))

        if not stripe_customer:
            self.create_stripe_customers([self.invoice.profile])

    def validate_invoice_offer_in_stripe(self):
        offer_to_create = []
        for order_item in self.invoice.get_one_time_transaction_order_items():
            if not order_item.offer.meta.get('stripe'):
                offer_to_create.append(order_item.offer)

        self.create_offers(offer_to_create)

    def validate_invoice_subscriptions_in_stripe(self):
        subscriptions_to_create = []
        for order_item in self.invoice.get_recurring_order_items():
            if not order_item.offer.meta.get('stripe'):
                subscriptions_to_create.append(order_item.offer)

        self.create_offers(subscriptions_to_create)

    def get_stripe_webhook_endpoints(self):
        has_more = True
        endpoint_urls = []
        starting_after = None
        while has_more:
            stripe_endpoint_object = self.stripe.WebhookEndpoint.list(limit=1, starting_after=starting_after)
            
            if not isinstance(stripe_endpoint_object, self.stripe.ListObject):
                return endpoint_urls
            
            if (endpoints := stripe_endpoint_object.get("data", [])):
                has_more = stripe_endpoint_object.get("has_more", False)
                endpoint_urls.extend([endpoint.get("url") for endpoint in endpoints])
                if hasattr(stripe_endpoint_object.get("data", [])[-1:][0], "id"):
                    starting_after = stripe_endpoint_object.get("data", [])[-1:][0]['id']

        return endpoint_urls
    
    def check_stripe_has_invoice_payment_succeeded_endpoint(self):
        domain_sections = [self.site.domain]
        platform_base_domains = [base.lstrip(".") for base in settings.ALLOWED_HOSTS if base.startswith(".")]
        
        if len(platform_base_domains):
            domain_sections.append(platform_base_domains[0])
        
        host = ".".join(domain_sections)
        endpoint_to_check = f"https://{host}/administration/product/api/stripe/invoice/payment/succeded/"
        endpoints = self.get_stripe_webhook_endpoints()

        if endpoint_to_check not in endpoints:
            response = self.stripe.WebhookEndpoint.create(
                enabled_events=["invoice.payment_succeeded"],
                url=endpoint_to_check
            )

            if response.secret is None:
                logger.error(f"Stripe endpoint {endpoint_to_check} was not created {response}")

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
                'error': f"{e}",
                'user_message': user_message
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
        rounded_fraction = round(fraction_part, 2)

        whole_str = str(whole_part).split('.')[0]
        fraction_str = str(rounded_fraction).split('.')[1][:2]

        if len(fraction_str) < 2:
            fraction_str = fraction_str + "0"

        stripe_amount = int("".join([whole_str, fraction_str]))
            
        return stripe_amount

    def convert_integer_to_decimal(self, integer):
        if not integer:
            return 0
        
        return Decimal(f"{str(integer)[:-2]}.{str(integer)[-2:]}")
    
    def get_stripe_connect_account(self):
        stripe_connect = StripeConnectAccountConfig(self.site)

        if stripe_connect.instance:
            return stripe_connect.get_key_value('stripe_connect_account')

        return None

    def get_stripe_base_fee_amount(self, amount):
        stripe_base_fee = 0

        if STRIPE_BASE_COMMISSION.get('percentage'):
            stripe_base_fee = (amount * STRIPE_BASE_COMMISSION['percentage']) / 100

        if STRIPE_BASE_COMMISSION.get('fixed'):
            stripe_base_fee += STRIPE_BASE_COMMISSION['fixed']

        return stripe_base_fee

    def get_application_fee_percent(self):
        vendor_site_commission = VendorSiteCommissionConfig(self.site)

        if vendor_site_commission.instance:
            return vendor_site_commission.get_key_value('commission')

        return 0
  
    def get_application_fee_amount(self, amount):
        vendor_site_commission = VendorSiteCommissionConfig(self.site)

        if vendor_site_commission.instance:
            return (vendor_site_commission.get_key_value('commission') * amount) / 100

        return 0

    def get_recurring_fee_amount(self, amount):
        fee = 0

        if STRIPE_RECURRING_COMMISSION.get('percentage'):
            fee = (amount * STRIPE_RECURRING_COMMISSION['percentage']) / 100

        if STRIPE_RECURRING_COMMISSION.get('fixed'):
            fee += STRIPE_RECURRING_COMMISSION['fixed']
        
        return fee
    
    def calculate_fee_percentage(self, invoice_amount, fees):

        total_fee_percentage = (fees * 100) / invoice_amount

        return Decimal(total_fee_percentage).quantize(Decimal('.00'), rounding=ROUND_UP)

    def get_invoice_status(self, stripe_status):
        if stripe_status in ["draft", ]:
            return InvoiceStatus.CART
        elif stripe_status in ["paid", "uncollectible", "open", "void"]:
            return InvoiceStatus.COMPLETE

    def get_payment_status(self, stripe_status, is_refund):
        if is_refund:
            return PurchaseStatus.REFUNDED
        
        if stripe_status == "pending":
            return PurchaseStatus.QUEUED
        elif stripe_status == "succeeded":
            return PurchaseStatus.SETTLED
        elif stripe_status == "failed":
            return PurchaseStatus.DECLINED

    def get_subscription_status(self, stripe_status):
        if stripe_status in ["active", "trialing"]:
            return SubscriptionStatus.ACTIVE
        elif stripe_status == "paused":
            return SubscriptionStatus.PAUSED
        elif stripe_status == "canceled":
            return SubscriptionStatus.CANCELED
        elif stripe_status in ["past_due", "unpaid", "incomplete"]:
            return SubscriptionStatus.SUSPENDED
        elif stripe_status == "incomplete_expired":
            return SubscriptionStatus.EXPIRED

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
        object_data['id'] = object_id
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
        
    def stripe_update_object_metadata(self, stripe_object_class, object_id, metadata):
        object_data = {}
        object_data['sid'] = object_id
        object_data['metadata'] = metadata

        stripe_object = self.stripe_call(stripe_object_class.modify, object_data)

        if self.transaction_succeeded:
            self.transaction_succeeded = False
            return stripe_object

        return None

    # Stripe Object Builders
    ##########
    def build_transfer_data(self):
        if not self.get_stripe_connect_account():
            return None
        
        return {
            'destination': self.get_stripe_connect_account(),
            # Not required if you are using the application_fee parameter
            # 'amount_percent': 100 - self.get_application_fee_percent()
        }

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
   
    def build_price(self, price, currency):
        if 'stripe' not in price.offer.meta or 'product_id' not in price.offer.meta['stripe']:
            raise TypeError(f"Price cannot be created without a product_id on price.offer.meta['stripe'] field offer: {price.offer}")

        price_data = {
            'active': True,
            'product': price.offer.meta['stripe']['product_id'],
            'currency': currency,
            'unit_amount': self.convert_decimal_to_integer(price.cost),
            'metadata': {
                'site': price.offer.site.domain,
                'pk': price.pk
            }
        }
        
        if price.offer.terms < TermType.PERPETUAL:
            price_data['recurring'] = {
                'interval': 'month' if price.offer.term_details['term_units'] == TermDetailUnits.MONTH else 'year',
                'interval_count': price.offer.term_details['period_length'],
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
                'number': self.payment_info.cleaned_data.get('card_number'),
                'exp_month': self.payment_info.cleaned_data.get('expire_month'),
                'exp_year': self.payment_info.cleaned_data.get('expire_year'),
                'cvc': self.payment_info.cleaned_data.get('cvv_number'),
            },
            'billing_details': {
                'address': {
                    'line1': self.billing_address.cleaned_data.get('address_1', None),
                    'line2': self.billing_address.cleaned_data.get('address_2', None),
                    'city': self.billing_address.cleaned_data.get("locality", ""),
                    'state': self.billing_address.cleaned_data.get("state", ""),
                    'country': Country.names[Country.values.index(int(self.billing_address.cleaned_data.get("country")))],
                    'postal_code': self.billing_address.cleaned_data.get("postal_code")
                },
                'name': self.payment_info.cleaned_data.get('full_name', None),
                'email': self.invoice.profile.user.email
            }
        }

    def build_payment_intent(self, amount, payment_method_id, currency=DEFAULT_CURRENCY):
        stripe_base_fee = self.get_stripe_base_fee_amount(amount)
        application_fee = self.get_application_fee_amount(amount)

        fee_amount = self.convert_decimal_to_integer(stripe_base_fee + application_fee)

        return {
            'amount': self.convert_decimal_to_integer(amount),
            'currency': currency,
            'customer': self.invoice.profile.meta['stripe_id'],
            'application_fee_amount': fee_amount,
            'payment_method': payment_method_id,
            'transfer_data': {
                "destination": self.get_stripe_connect_account(),
            },
            'on_behalf_of': self.get_stripe_connect_account()
        }

    def build_setup_intent(self, payment_method_id):
        return {
            'customer': self.invoice.profile.meta['stripe_id'],
            'confirm': True,
            'payment_method_types': ['card'],
            'payment_method': payment_method_id,
            'metadata': {'site': self.invoice.site},
            'on_behalf_of': self.get_stripe_connect_account()
        }
    
    def build_subscription(self, subscription, payment_method_id):
        price = subscription.offer.get_current_price_instance()
        sub_discount = 0
        promotion_code = None
        total_fee_percentage = None
        has_connected_account = self.get_stripe_connect_account()

        if hasattr(self.invoice, 'coupon_code') and (coupon_code := self.invoice.coupon_code.first()):
            promotion_code = coupon_code.meta['stripe_id']

            if coupon_code.does_offer_apply(price.offer):
                sub_discount = coupon_code.get_discounted_amount(price.offer)

        # Stripe Fees are not adjusted by the discount until discount duration has been implemented
        if has_connected_account:
            stripe_base_fee = self.get_stripe_base_fee_amount(price.cost)
            stripe_recurring_fee = self.get_recurring_fee_amount(price.cost)
            application_fee = self.get_application_fee_amount(price.cost)

            if (price.cost - sub_discount) < (stripe_base_fee + stripe_recurring_fee + application_fee):
                self.transaction_info["errors"] = {
                    "user_message": f"Invoice total: ${(price.cost - sub_discount):.2f} is less than the fee's ${(stripe_base_fee + stripe_recurring_fee + application_fee):.2f} needed to be collected"
                }
                self.transaction_succeeded = False
                return None
        
            total_fee_percentage = self.calculate_fee_percentage(
                price.cost - sub_discount,
                stripe_base_fee + stripe_recurring_fee + application_fee
            )

        return {
            'customer': self.invoice.profile.meta['stripe_id'],
            'promotion_code': promotion_code,
            'items': [{'price': subscription.offer.meta['stripe']['prices'][str(price.pk)]}],
            'default_payment_method': payment_method_id,
            'metadata': {'site': self.invoice.site},
            'trial_period_days': subscription.offer.get_trial_days(),
            'application_fee_percent': total_fee_percentage,
            'transfer_data': self.build_transfer_data(),
            'on_behalf_of': self.get_stripe_connect_account()
        }

    def build_invoice_line_item(self, order_item, invoice_id):
        price = order_item.offer.get_current_price_instance()

        line_item = {
            'customer': self.invoice.profile.meta.get('stripe_id'),
            'invoice': invoice_id,
            'quantity': order_item.quantity,
            'price': order_item.offer.meta['stripe']['prices'].get(str(price.pk)),
        }

        if order_item.offer.has_trial() or order_item.offer.has_valid_billing_start_date() or order_item.offer.discount():
            line_item['discounts'] = [{'coupon': order_item.offer.meta['stripe'].get('coupon_id')}]

        return line_item

    def build_invoice(self, currency=DEFAULT_CURRENCY):
        return {
            'customer': self.invoice.profile.meta.get('stripe_id'),
            'currency': currency,
            'on_behalf_of': self.get_stripe_connect_account()
        }

    def build_refund(self, refund_form):
        int_amount = self.convert_decimal_to_integer(refund_form.cleaned_data["refund_amount"])
        return {
            "charge": refund_form.instance.transaction,
            "amount": int_amount,
            "reverse_transfer": True,
            "refund_application_fee": True,
            "reason": refund_form.cleaned_data['reason']
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
        
    def get_customer_profile(self, stripe_customer, site=None):
        """Get's CustomerProfile if found.
        Try's to get the CustomerProfile based on the stripe_customer.email and site.
        If found and the CustomerProfile instance does not have the associated stripe_customer.id it addes it addes it to the meta field.

        Args:
            site: Site instance
            stripe_customer: Stripe Customer Object

        Returns:
            CustomerProfile Instance or None
        """
        customer_profile = None
        if not site:
            site = self.site

        try:
            customer_profile = CustomerProfile.objects.get(site=site, user__email=stripe_customer.email)
        except ObjectDoesNotExist:
            logger.error(f"get_customer_profile CustomerProfile Not Found email:{stripe_customer.email} site: {site.domain}")
        except MultipleObjectsReturned:
            logger.error(f"get_customer_profile Multiple CustomerProfiles returned for email:{stripe_customer.email} site: {site.domain}")
        except Exception as exce:
            logger.error(f"get_customer_profile Exception: {exce} for email:{stripe_customer.email} site: {site.domain} ")

        if customer_profile and 'stripe_id' not in customer_profile.meta:
            customer_profile.meta.update({'stripe_id': stripe_customer.id})
            customer_profile.save()

        return customer_profile

    def get_customer_profile_and_stripe_customer(self, stripe_customer_id):
        """Gets CustomerProfile and Stripe Customer using Stripe Customer ID
        
            Args:
                stripe_customer_id: Stripe Customer ID
            
            Returns:
                CustomerProfile Instance or None
                Stripe Customer Object or None
        """
        stripe_customer = None
        customer_profile = None
        
        stripe_customer = self.stripe_get_object(self.stripe.Customer, stripe_customer_id)
        if not stripe_customer:
            logger.info(f"Stripe Customer was not found: {stripe_customer_id}")
            return customer_profile, stripe_customer

        customer_profile = self.get_customer_profile(stripe_customer)
        if not customer_profile:
            logger.info(f"Customer Profile not found for stripe_customer {stripe_customer.id} site: {self.site}")
            return customer_profile, stripe_customer

        return customer_profile, stripe_customer
    
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
                profile.meta.update({'stripe_id': new_stripe_customer['id']})
                profile.save()
                logger.info(f"create_stripe_customers: Stripe Customer created: {new_stripe_customer['id']} from profile: {profile} site: {profile.site}")

    def update_stripe_customers(self, customers):
        for profile in customers:
            customer_id = profile.meta.get('stripe_id')
            profile_data = self.build_customer(profile)
            existing_stripe_customer = self.stripe_update_object(self.stripe.Customer, customer_id, profile_data)

            if existing_stripe_customer:
                profile.meta.update({'stripe_id': existing_stripe_customer['id']})
                profile.save()
                logger.info(f"update_stripe_customers: Stipe Customer updated: {existing_stripe_customer['id']} from profile: {profile} site: {profile.site}")
            else:
                self.create_stripe_customers([profile])
    
    def get_customer_payment_methods(self, customer_id):
        payment_methods = self.stripe_call(self.stripe.Customer.list_payment_methods, customer_id)

        if not payment_methods.data:
            return None

        return payment_methods.data

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

    def get_stripe_customer_from_email(self, email):
        query_builder = StripeQueryBuilder()

        email_clause = query_builder.make_clause_template(
            field='email',
            value=email,
            operator=query_builder.EXACT_MATCH
        )
        
        query = query_builder.build_search_query(self.stripe.Customer, [email_clause])
        query_result = self.stripe_query_object(self.stripe.Customer, query)

        if len(query_result['data']) == 1:
            return query_result['data'][0]
        elif len(query_result['data']) > 1:
            logger.info(f"Multiple stripe customer found for email: {email} on site: {self.site}")
        else:
            logger.info(f"No Stripe Customer Found for email: {email} on site: {self.site}")
        
        return None

    ##########
    # Offers/Products
    ##########
    def get_stripe_product(self, site, pk):
        pk_clause = self.query_builder.make_clause_template(
            field='metadata',
            key='pk',
            value=str(pk),
            operator=self.query_builder.EXACT_MATCH,
            next_operator=self.query_builder.AND
        )
        site_clause = self.query_builder.make_clause_template(
            field='metadata',
            key='site',
            value=site.domain,
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Product, [pk_clause, site_clause])
        search_data = self.stripe_query_object(self.stripe.Product, {'query': query})

        if search_data:
            return search_data.data[0]
        
        return None

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

    def get_site_stripe_products(self, site):
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
        offers = Offer.objects.filter(site=site, pk__in=offer_pk_list).exclude(is_promotional=True)
        return offers

    def get_vendor_offers_not_in_stripe(self, offer_pk_list, site):
        offers = Offer.objects.filter(site=site).exclude(pk__in=offer_pk_list).exclude(is_promotional=True)
        return offers

    def create_stripe_product(self, offer):
        product_data = self.build_product(offer)

        stripe_product = self.stripe_create_object(self.stripe.Product, product_data)

        if not stripe_product:
            logger.error(f"create_stripe_product error: {self.transaction_info}")
            return None
        
        if 'stripe' in offer.meta:
            offer.meta['stripe']['product_id'] = stripe_product['id']
        else:
            offer.meta['stripe'] = {'product_id': stripe_product['id']}

        offer.save()
        logger.info(f"create_stripe_product Stripe Product created: {stripe_product.id} from offer {offer} site {offer.site}")
        return stripe_product
    
    def create_offers(self, offers):
        for offer in offers:
            # build product first, since product_id is needed to build price later
            self.create_stripe_product(offer)

            # TODO: Need to explore what is the best way to upload prices in each currency
            # currently we will only support the default currency (DEFAULT_CURRENCY) se
            # on the vendor.config.py file
            # for currency in AVAILABLE_CURRENCIES:
            #     ...
            self.create_stripe_product_prices(offer)

    def sync_offer(self, offer):
        product_id = offer.meta['stripe']['product_id']
        product_data = self.build_product(offer)
        stripe_product = self.stripe_update_object(self.stripe.Product, product_id, product_data)
        
        if not stripe_product:
            self.create_offers([offer])
        
        if 'stripe' in offer.meta:
            offer.meta['stripe']['product_id'] = stripe_product['id']
        else:
            offer.meta['stripe'] = {'product_id': stripe_product['id']}
        
        offer.save()
        return stripe_product

    def update_offers(self, offers):
        for offer in offers:
            self.sync_offer(offer)
            # Handle Price
            # TODO: Need to explore what is the best way to upload prices in each currency
            # currently we will only support the default currency (DEFAULT_CURRENCY) se
            # on the vendor.config.py file
            # for currency in AVAILABLE_CURRENCIES:
            #     ...
            self.sync_offer_prices(offer)

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
  
    def get_offer_from_stripe_product(self, stripe_product):
        offer = None

        if "pk" not in stripe_product.metadata:
            logger.error(f"get_offer_from_stripe_product stripe_product id: ({stripe_product.id}, {stripe_product.name}) does not have a pk in metadata")
            return offer
        
        try:
            offer = Offer.objects.get(pk=int(stripe_product.metadata["pk"]))
        except ObjectDoesNotExist:
            logger.error(f"get_offer_from_stripe_product Offer Does Not Exists for stripe_product: ({stripe_product.id}, {stripe_product.name}) pk: {stripe_product.metadata['pk']}")
        except MultipleObjectsReturned:
            logger.error(f"get_offer_from_stripe_product Multiple Offers Found for stripe_product: ({stripe_product.id}, {stripe_product.name}) pk: {stripe_product.metadata['pk']}")
        except Exception as exce:
            logger.error(f"get_offer_from_stripe_product Exception {exce} for stripe_product: ({stripe_product.id}, {stripe_product.name}) pk: {stripe_product.metadata['pk']}")
        
        return offer

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

    def create_stripe_product_prices(self, offer):
        for price in offer.prices.all():
            price_data = self.build_price(price, DEFAULT_CURRENCY)
            stripe_price = self.stripe_create_object(self.stripe.Price, price_data)
            
            if not stripe_price:
                logger.error(f"create_stripe_product_prices price not created: {self.transaction_info}")
                return None
            
            if 'stripe' not in offer.meta:
                offer.meta = {'stripe': {'prices': {price.pk: stripe_price.id}}}
            elif 'prices' in offer.meta['stripe']:
                offer.meta['stripe']['prices'].update({price.pk: stripe_price.id})
            else:
                offer.meta['stripe'].update({'prices': {price.pk: stripe_price.id}})

            offer.save()
            logger.info(f"create_stripe_product_prices: Stripe Price created: {stripe_price.id} from offer {offer} site {offer.site}")

    def sync_offer_prices(self, offer):
        stripe_product_prices = self.get_stripe_prices_for_product(offer.meta['stripe']['product_id'])

        if not stripe_product_prices:
            self.create_stripe_product_prices(offer)
            return None
        
        current_price = offer.get_current_price_instance()
        
        for stripe_price in stripe_product_prices:
            try:
                price = offer.prices.get(pk=stripe_price.metadata['pk'])
            except ObjectDoesNotExist:
                self.stripe_delete_object(self.stripe.Price, stripe_price.id)
            
            price_data = self.build_price(price, DEFAULT_CURRENCY) | {'active': False}
            if current_price == price:
                price_data['active'] = True
            
            price_data.pop('unit_amount', None)
            price_data.pop('product', None)
            price_data.pop('currency', None)
            price_data.pop('recurring', None)

            self.stripe_update_object(self.stripe.Price, stripe_price.id, price_data)

            if 'stripe' not in offer.meta:
                offer.meta = {'stripe': {'prices': {price.pk: stripe_price.id}}}
            elif 'prices' in offer.meta['stripe']:
                offer.meta['stripe']['prices'].update({price.pk: stripe_price.id})
            else:
                offer.meta['stripe'].update({'prices': {price.pk: stripe_price.id}})
            offer.save()
            
            logger.info(f"sync_offer_prices: Stripe Price Updated: ({stripe_price.id}, {price.pk})")

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
    # Invoice
    ##########
    def get_subscription_invoices(self, subscription_id):
        subscription_clause = self.query_builder.make_clause_template(
            field='subscription',
            value=subscription_id,
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Invoice, [subscription_clause, ])

        invoices = self.stripe_query_object(self.stripe.Invoice, {'query': query})

        return invoices.data

    def get_or_create_invoice_from_stripe_invoice(self, stripe_invoice, offer, customer_profile):
        invoice = None
        created = False

        try:
            invoice, created = Invoice.objects.get_or_create(
                site=customer_profile.site,
                vendor_notes__has_key="stripe_id",
                vendor_notes__stripe_id=stripe_invoice.id,
                profile=customer_profile,
                defaults={
                    "vendor_notes": {'stripe_id': stripe_invoice.id},
                    "status": self.get_invoice_status(stripe_invoice.status),
                    "ordered_date": timezone.datetime.fromtimestamp(stripe_invoice.created, tz=timezone.utc)
                }
            )
        except MultipleObjectsReturned:
            logger.error(f"get_or_create_invoice_from_stripe_invoice Multiple Invoice for id: {stripe_invoice.id} customer_profile: {customer_profile.user.email}")
            invoice = Invoice.objects.filter(
                site=customer_profile.site,
                vendor_notes__has_key="stripe_id",
                vendor_notes__stripe_id=stripe_invoice.id,
                profile=customer_profile,
            ).first()
        except Exception as exce:
            logger.error(f"get_or_create_invoice_from_stripe_invoice Exception {exce} for id: {stripe_invoice.id} customer_profile: {customer_profile.user.email}")

        if created:
            invoice.empty_cart()
            invoice.add_offer(offer)
            invoice.total = self.convert_integer_to_decimal(stripe_invoice.total)
            logger.info(f"get_or_create_invoice_from_stripe_invoice Invoice Created: ({invoice.pk}, {stripe_invoice.id})")
        
        invoice.status = self.get_invoice_status(stripe_invoice.status)
        invoice.save()

        return invoice, created

    def get_offers_from_invoice_line_items(self, stripe_line_items):
        offers = []
        
        for line_item in stripe_line_items:
            stripe_product = self.stripe_get_object(self.stripe.Product, line_item.product)

            offer = self.get_offer_from_stripe_product(stripe_product)
            if offer:
                offers.append(offer)

        return offers
        
    ##########
    # Payments and Receipts
    ##########
    def get_or_create_payment_from_stripe_payment_and_charge(self, invoice, stripe_payment_method, stripe_charge):
        payment = None
        created = False

        try:
            payment, created = Payment.objects.get_or_create(
                transaction=stripe_charge.id,
                defaults={
                    "profile": invoice.profile,
                    "amount": self.convert_integer_to_decimal(stripe_charge.amount_captured),
                    "invoice": invoice,
                    "submitted_date": timezone.datetime.fromtimestamp(stripe_charge.created, tz=timezone.utc),
                    "transaction": stripe_charge.id,
                    "status": self.get_payment_status(stripe_charge.status, stripe_charge.refunded),
                    "success": stripe_charge.paid,
                    "payee_full_name": stripe_payment_method['billing_details']['name'],
                    "result": {
                        'account_number': stripe_payment_method['card']['last4'] if "card" in stripe_payment_method else "",
                        'full_name': stripe_payment_method['billing_details']['name']
                    }
                }
            )
        except MultipleObjectsReturned:
            dup_payments = Payment.objects.filter(transaction=stripe_charge.id)
            payment = dup_payments.first()
            logger.error(f"get_or_create_payment_from_stripe_payment_and_charge Multiple Payments for transaction: {stripe_charge.id} queryresult for payments: {dup_payments}")
        except Exception as exce:
            logger.error(f"get_or_create_payment_from_stripe_payment_and_charge Exception {exce} for stripe_charge id: {stripe_charge.id}")

        if created:
            logger.info(f"get_or_create_payment_from_stripe_payment_and_charge: Payment Created ({payment.pk},{stripe_charge.id})")
            
        return payment, created

    def get_or_create_subscription_receipt_from_stripe_charge(self, invoice, payment, stripe_charge):
        receipt = None
        created = False
        try:
            receipt, created = Receipt.objects.get_or_create(
                profile=invoice.profile,
                transaction=stripe_charge.id,
                defaults={
                    "order_item": invoice.order_items.first(),
                    "start_date": timezone.datetime.fromtimestamp(stripe_charge.created, tz=timezone.utc),
                    "end_date": invoice.order_items.first().offer.get_offer_end_date(start_date=timezone.datetime.fromtimestamp(stripe_charge.created, tz=timezone.utc)),
                    "subscription": payment.subscription,
                    "meta": payment.result | {"payment_amount": str(payment.amount)}
                }
            )
        except MultipleObjectsReturned:
            dup_receipts = Receipt.objects.filter(profile=invoice.profile, transaction=stripe_charge.id)
            receipt = dup_receipts.first()
            logger.info(f"get_or_create_receipt_from_stripe_charge Multiple Receipts for transaction: {stripe_charge.id}, duplicated receipts: {dup_receipts}")
        except Exception as exce:
            logger.error(f"get_or_create_receipt_from_stripe_charge Exception {exce} for stripe_charge id: {stripe_charge.id}, subscriptions: ({payment.subscription.pk},{payment.subscription.gateway_id})")

        if created:
            receipt.products.add(invoice.order_items.first().offer.products.first())
            logger.info(f"get_or_create_receipt_from_stripe_charge Receipt created: ({receipt.pk}, {stripe_charge.id})")

        return receipt, created
    
    def create_single_purchase_receipts(self, invoice, payment, stripe_charge):
        receipt = None
        created = False

        for order_item in invoice.get_one_time_transaction_order_items():
            try:
                receipt, created = Receipt.objects.get_or_create(
                    profile=invoice.profile,
                    transaction=stripe_charge.id,
                    defaults={
                        "order_item": order_item,
                        "start_date": timezone.datetime.fromtimestamp(stripe_charge.created, tz=timezone.utc),
                        "end_date": order_item.offer.get_offer_end_date(start_date=timezone.datetime.fromtimestamp(stripe_charge.created, tz=timezone.utc)),
                        "subscription": payment.subscription,
                        "meta": payment.result | {"payment_amount": str(payment.amount)}
                    }
                )
            except MultipleObjectsReturned:
                dup_receipts = Receipt.objects.filter(profile=invoice.profile, transaction=stripe_charge.id)
                receipt = dup_receipts.first()
                logger.info(f"get_or_create_receipt_from_stripe_charge Multiple Receipts for transaction: {stripe_charge.id}, duplicated receipts: {dup_receipts}")
            except Exception as exce:
                logger.error(f"get_or_create_receipt_from_stripe_charge Exception {exce} for stripe_charge id: {stripe_charge.id}, subscriptions: ({payment.subscription.pk},{payment.subscription.gateway_id})")

            if created:
                receipt.products.add(order_item.offer.products.first())
                logger.info(f"get_or_create_receipt_from_stripe_charge Receipt created: ({receipt.pk}, {stripe_charge.id})")

    ##########
    # Subscriptions
    ##########
    def get_stripe_subscriptions(self, site):
        clause = self.query_builder.make_clause_template(
            field="metadata",
            key="site",
            value=site.domain,
            operator=self.query_builder.EXACT_MATCH
        )

        query = self.query_builder.build_search_query(self.stripe.Subscription, [clause])

        subscription_search = self.get_all_stripe_search_objects(self.stripe.Subscription, {'query': query})

        return subscription_search

    def get_or_create_subscription_from_stripe_subscription(self, customer_profile, stripe_subscription):
        created = False
        subscription = None
        try:
            subscription, created = Subscription.objects.get_or_create(
                profile=customer_profile,
                gateway_id=stripe_subscription.id)
        except MultipleObjectsReturned:
            logger.error(f"get_or_create_subscription_from_stripe_subscription Multiple Subscriptions returned for customer_profile: {customer_profile} subscription: {stripe_subscription.id}")
        except Exception as exce:
            logger.error(f"get_or_create_subscription_from_stripe_subscription Exception {exce} for customer_profile: {customer_profile} subscription {stripe_subscription.id}")
        
        if subscription:
            subscription.status = self.get_subscription_status(stripe_subscription.status)
            subscription.save()
        
        if created:
            logger.info(f"get_or_create_subscription_from_stripe_subscription Subscription Created: ({subscription.pk}, {stripe_subscription.id})")

        return subscription, created
    
    def get_subscription(self, stripe_subscription):
        subscription = None
        try:
            subscription = Subscription.objects.get(gateway_id=stripe_subscription.id)
        except ObjectDoesNotExist:
            logger.error(f"Subscription does not exists for Stripe Subscription: {stripe_subscription.id}")
            return None
        except MultipleObjectsReturned:
            logger.error(f"Multiple Subscriptions found for Stripe Subscription: {stripe_subscription.id}")
        except Exception as exce:
            logger.error(f"Get Subscription Exception: {exce} for Stripe Subscription {stripe_subscription.id}")
        
        return subscription
    
    def create_subscription(self, payment_method_id, subscription_extras):
        """Creates a Stripe and Vendor Subscriptions instance
        
        Method setups the process to create and charge a Stripe Subscription. If a Stripe Subscription
        object is returned a Vendor Subscrption instance will be created. Otherwise an excepetion
        will be raise with the reason of why the subscription failed to create.
        
        Args:
            payment_method_id: String coming from a Stripe Payment Method Object
            
            subscription_extras: Dictionary containing extra arguments for the Stripe Subscription.
            EG { "trail_days": 10, "billing_cycle_anchor": <datetime>}
        
        Returns:
            subscription: Vendor Subscription Model instance
            
        Exceptions:
            Stripe Setup Intent failed to create
            
            Stripe Subscription failed to create
        """
        setup_intent_object = self.build_setup_intent(payment_method_id)
        stripe_setup_intent = self.stripe_create_object(self.stripe.SetupIntent, setup_intent_object)
        if not stripe_setup_intent:
            raise Exception(f"Could not create stripe_setup_intent transaction_info: {self.transaction_info}")
        
        subscription_obj = self.build_subscription(self.invoice.order_items.first(), payment_method_id)
        subscription_obj |= subscription_extras

        stripe_subscription = self.stripe_create_object(self.stripe.Subscription, subscription_obj)
        if not stripe_subscription or stripe_subscription.status == 'incomplete':
            self.transaction_succeeded = False
            raise Exception(f"Subscription Failed to be created: {self.transaction_info}")

        subscription = Subscription.objects.create(
            gateway_id=stripe_subscription.id,
            profile=self.invoice.profile,
            auto_renew=True,
            status=SubscriptionStatus.ACTIVE
        )
        subscription.meta['response'] = self.transaction_info
        subscription.save()

        return subscription

    def transfer_existing_customer_subscription_to_stripe(self, customer_profile):
        transfer_result_msg = {"success": [], "failed": []}
        for subscription in customer_profile.subscriptions.filter(status=SubscriptionStatus.ACTIVE):
            invoice = customer_profile.get_cart_or_checkout_cart()
            invoice.empty_cart()
            self.invoice = invoice
            last_start_date = subscription.receipts.last().start_date
            stripe_subscription = self.stripe_get_object(self.stripe.Subscription, subscription.gateway_id)
            offer = subscription.get_offer()

            if offer and not stripe_subscription:
                invoice.add_offer(offer)

                try:
                    self.pre_authorization()

                    payment_method_data = self.build_payment_method()
                    stripe_payment_method = self.stripe_create_object(self.stripe.PaymentMethod, payment_method_data)
                    if not stripe_payment_method:
                        raise Exception(f"Could not create stripe_payment_method transaction_info: {self.transaction_info}")
                    
                    subscription_extras = {
                        "billing_cycle_anchor": offer.get_offer_end_date(last_start_date),
                        "proration_behavior": PRORATION_BEHAVIOUR_CHOICE.NONE.value
                    }
                    self.create_subscription(offer, subscription_extras)

                    transfer_result_msg['success'].append(f"Successfuly Transfered Subscription: {subscription.gateway_id}")
                    self.update_invoice_status(InvoiceStatus.COMPLETE)
                    
                except Exception as exce:
                    logger.error(f"Creating Subscription Failed, transaction_info: {self.transaction_info}, exception: {exce}")
                    transfer_result_msg['failed'].append(f"Failed Transfer Subscription {subscription.gateway_id}, exception: {exce}")

            # TODO: Need to loop throught the SupportedPaymentProcessor to cancel the previous subscription.
            # But need to find a way in which we don't import the Processors to avoid having them to install
            # all them as a dependency
            subscription.status = SubscriptionStatus.CANCELED
            subscription.save()
            
        return transfer_result_msg
    
    ##########
    # Sync Vendor and Stripe
    ##########
    # TODO: function to deprecate.
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
        logger.info("StripeProcessor sync_customers Started")
        stripe_customers = self.get_stripe_customers(site)
        stripe_customers_emails = [customer_obj['email'] for customer_obj in stripe_customers]

        vendor_customers_in_stripe = self.get_vendor_customers_in_stripe(stripe_customers_emails, site)

        vendor_customers_with_stripe_meta = vendor_customers_in_stripe.filter(meta__has_key='stripe_id')
        vendor_customers_without_stripe_meta = vendor_customers_in_stripe.exclude(meta__has_key='stripe_id')

        vendor_customers_not_in_stripe = self.get_vendor_customers_not_in_stripe(stripe_customers_emails, site)
        vendor_customer_to_create = vendor_customers_not_in_stripe | vendor_customers_without_stripe_meta

        self.create_stripe_customers(vendor_customer_to_create)
        self.update_stripe_customers(vendor_customers_with_stripe_meta)
        logger.info("StripeProcessor sync_customers Finished")

    def sync_offers(self, site):
        logger.info("StripeProcessor sync_offers Started")
        stripe_products = self.get_site_stripe_products(site)
        offer_pk_list = [product['metadata']['pk'] for product in stripe_products]

        offers_in_vendor = self.get_vendor_offers_in_stripe(offer_pk_list, site)

        offers_in_vendor_with_stripe_meta = offers_in_vendor.filter(meta__has_key='stripe')
        offers_in_vendor_without_stripe_meta = offers_in_vendor.exclude(meta__has_key='stripe')
        
        offers_to_create = self.get_vendor_offers_not_in_stripe(offer_pk_list, site)

        for update_offer_meta in offers_in_vendor_without_stripe_meta:
            for stripe_product in stripe_products:
                if stripe_product['metadata']['pk'] == update_offer_meta.pk:
                    update_offer_meta.meta.update({'stripe': {'product_id': stripe_product.id}})
                    update_offer_meta.save()

        self.create_offers(offers_to_create)
        self.update_offers(offers_in_vendor_with_stripe_meta | offers_in_vendor_without_stripe_meta)
        logger.info("StripeProcessor sync_offers Finished")

    def sync_stripe_subscription(self, site, stripe_subscription):
        stripe_customer = self.stripe_get_object(self.stripe.Customer, stripe_subscription.customer)
        customer_profile = self.get_customer_profile(stripe_customer, site)
        
        if customer_profile:
            subscription, created = self.get_or_create_subscription_from_stripe_subscription(customer_profile, stripe_subscription)

            stripe_product = self.stripe_get_object(self.stripe.Product, stripe_subscription.plan.product)
            offer = self.get_offer_from_stripe_product(stripe_product)
            
            if offer:
                stripe_sub_invoices = self.get_subscription_invoices(stripe_subscription.id)
                
                for stripe_invoice in stripe_sub_invoices:
                    invoice, created = self.get_or_create_invoice_from_stripe_invoice(stripe_invoice, offer, customer_profile)
                        
                    if stripe_invoice.charge:
                        stripe_charge = self.stripe_get_object(self.stripe.Charge, stripe_invoice.charge)
                        stripe_payment_method = self.stripe_get_object(self.stripe.PaymentMethod, stripe_charge.payment_method)
                        
                        payment, created = self.get_or_create_payment_from_stripe_payment_and_charge(invoice, stripe_payment_method, stripe_charge)
                        if created:
                            payment.subscription = subscription
                            payment.save()

                        if payment.status == PurchaseStatus.SETTLED:
                            receipt, created = self.get_or_create_subscription_receipt_from_stripe_charge(invoice, payment, stripe_charge)

    def sync_stripe_subscriptions(self, site):
        logger.info("sync_stripe_subscriptions Started")
        stripe_subscriptions = self.get_stripe_subscriptions(site)

        for stripe_subscription in stripe_subscriptions:
            logger.info(f"sync_stripe_subscriptions: syncing subscription: {stripe_subscription.id}")
            self.sync_stripe_subscription(site, stripe_subscription)

        logger.info("sync_stripe_subscriptions Ended")

    def sync_stripe_vendor_objects(self, site):
        """
        Sync up all the CustomerProfiles, Offers, Prices, and Coupons for all of the sites
        """
        logger.info("StripeProcessor sync_stripe_vendor_objects Started")
        self.sync_customers(site)
        self.sync_offers(site)
        self.sync_stripe_subscriptions(site)
        logger.info("StripeProcessor sync_stripe_vendor_objects Finished")

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
        self.validate_invoice_customer_in_stripe()
        self.validate_invoice_offer_in_stripe()
        self.validate_invoice_subscriptions_in_stripe()

        if settings.VENDOR_STATE == "PRODUCTION":
            self.check_stripe_has_invoice_payment_succeeded_endpoint()

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
        
        self.invoice.vendor_notes['stripe_id'] = stripe_invoice.id
        self.invoice.save()
        
        stripe_line_items = []
        for order_item in self.invoice.get_one_time_transaction_order_items():
            line_item_data = self.build_invoice_line_item(order_item, stripe_invoice.id)
            stripe_line_item = self.stripe_create_object(self.stripe.InvoiceItem, line_item_data)

            if not stripe_line_item:
                return None
            
            stripe_line_items.append(stripe_line_item)

        stripe_invoice.lines = stripe_line_items

        amount = self.invoice.get_one_time_transaction_total()

        stripe_base_fee = self.get_stripe_base_fee_amount(amount)
        application_fee = self.get_application_fee_amount(amount)
        fee_amount = self.convert_decimal_to_integer(stripe_base_fee + application_fee)

        invoice_update = {
            'application_fee_amount': fee_amount,
            'transfer_data': {
                "destination": self.get_stripe_connect_account(),
            },
        }

        stripe_invoice = self.stripe_update_object(stripe.Invoice, stripe_invoice.id, invoice_update)
        if not stripe_invoice:
            return None

        self.stripe_call(stripe_invoice.pay, {"payment_method": stripe_payment_method.id})

        if self.transaction_succeeded:
            self.transaction_id = stripe_invoice.payment_intent

    def subscription_payment(self, subscription):
        """Creates and process the payment for the subscription
        Creates a Stripe Payment Method, a Stripe Setup Intent and a Stripe Subscription. This are the
        objects needed by Stripe to process a payment for the subscriptions being created.
        
        If the transaction is successful it will set the self.transaction_success variable to true, saves
        the invoice number to the invoice.vendor_notes field and sets the self.subscription_id to the
        newley created stripe_subscription.id object.

        If the transaction fails, self.transaction_success is set to False.

        Args:
            subscription: OrderItem model instance.
        """
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
        if not subscription_obj:
            return None
        
        stripe_subscription = self.stripe_create_object(self.stripe.Subscription, subscription_obj)
        if not stripe_subscription or stripe_subscription.status == 'incomplete':
            self.transaction_succeeded = False
            return None

        if self.invoice.vendor_notes is None:
            self.invoice.vendor_notes = {}

        self.invoice.vendor_notes['stripe_id'] = stripe_subscription.latest_invoice
        self.invoice.save()

        self.subscription_id = stripe_subscription.id

    def charge_customer_profile(self):
        invoice_data = self.build_invoice()
        stripe_invoice = self.stripe_create_object(self.stripe.Invoice, invoice_data)
        if not stripe_invoice:
            return None

        stripe_customer_payment_methods = self.get_customer_payment_methods(self.invoice.profile.meta['stripe_id'])
        if not stripe_customer_payment_methods:
            return None
        
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

        self.stripe_call(stripe_invoice.pay, {"payment_method": stripe_customer_payment_methods[0].id})

        if self.transaction_succeeded:
            self.transaction_id = stripe_invoice.payment_intent

    def subscription_cancel(self, subscription):
        stripe_subscription = self.stripe_delete_object(self.stripe.Subscription, subscription.gateway_id)
        
        if stripe_subscription.status != "canceled":
            logger.error(f"Stripe Subscription Failed: subscription: {subscription.id} transaction info: {self.transaction_info}")
            raise Exception("Stripe Subscription Failed")
        
        super().subscription_cancel(subscription)

    def subscription_update_payment(self, subscription):
        """
        Updates the credit card information for the subscription in stripe
        and updates the subscription model in vendor.
        """

        stripe_subscription_object = self.stripe_get_object(self.stripe.Subscription, subscription.gateway_id)
        if not stripe_subscription_object:
            return None

        current_payment_method = self.stripe.Customer.retrieve_payment_method(
            stripe_subscription_object.customer,
            stripe_subscription_object.default_payment_method
        )

        payment_method_data = {
            'type': 'card',
            'card': {
                'number': self.payment_info.cleaned_data.get('card_number'),
                'exp_month': self.payment_info.cleaned_data.get('expire_month'),
                'exp_year': self.payment_info.cleaned_data.get('expire_year'),
                'cvc': self.payment_info.cleaned_data.get('cvv_number'),
            },
            'billing_details': {
                'name': self.payment_info.cleaned_data.get('full_name', None),
                'email': subscription.profile.user.email
            }
        }
        # keep previous address
        if current_payment_method:
            payment_method_data['billing_details']['address'] = current_payment_method.billing_details.get("address")

        # create payment method using new card
        stripe_payment_method = self.stripe_create_object(self.stripe.PaymentMethod, payment_method_data)
        if not stripe_payment_method:
            return None

        setup_intent_object = {
            'customer': subscription.profile.meta['stripe_id'],
            'confirm': True,
            'payment_method_types': ['card'],
            'payment_method': stripe_payment_method.id,
            'metadata': {'site': subscription.profile.site}
        }

        # validate
        stripe_setup_intent = self.stripe_create_object(self.stripe.SetupIntent, setup_intent_object)
        if not stripe_setup_intent:
            return None

        # update subscription
        self.stripe.Subscription.modify(
            subscription.gateway_id,
            default_payment_method=stripe_payment_method
        )

        # save payment info to subscription model
        payment_info = {}
        account_number = payment_method_data.get("card", {}).get("number", "")[-4:]
        account_type = stripe_payment_method.card.get("brand", "")

        if account_number:
            payment_info['account_number'] = account_number

        if account_type:
            payment_info['account_type'] = account_type

        subscription.save_payment_info(payment_info)

    def refund_payment(self, refund_form, date=timezone.now()):
        refund_data = self.build_refund(refund_form)
        
        stripe_refund = self.stripe_create_object(self.stripe.Refund, refund_data)

        if stripe_refund:
            super().refund_payment(refund_form, date=timezone.datetime.fromtimestamp(stripe_refund.created, tz=timezone.utc))
