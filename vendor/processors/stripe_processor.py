"""
Payment processor for Stripe.
"""
import logging
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
from vendor.models import Offer

logger = logging.getLogger(__name__)

# def add_site_on_object_metadata(func):
#     # Decorate that check if the stripe object data has a metadata field that has site field.
#     # If it does not have one it addas it to kwargs
#     def wrapper(*args, **kwargs):
#         if 'metadata' not in kwargs or 'site' not in kwargs['metadata']:
#             kwargs['metadata'] = {'site': args[0].site}

#         return func(*args, kwargs)
    
#     return wrapper


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
    transaction_submitted = False
    source = None
    products_mapping = {}

    def processor_setup(self, site, source=None):
        self.credentials = StripeIntegration(site)
        self.source = source
        self.site = site
        self.stripe = stripe
        if self.credentials.instance:
            self.stripe.api_key = self.credentials.instance.private_key
        elif settings.STRIPE_SECRET_KEY:
            self.stripe.api_key = settings.STRIPE_SECRET_KEY
        else:
            logger.error("StripeProcessor missing keys in settings: STRIPE_PUBLIC_KEY")
            raise ValueError("StripeProcessor missing keys in settings: STRIPE_PUBLIC_KEY")

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

        self.transaction_submitted = False

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
        query_result = self.stripe_call(stripe_object_class.search, query)

        return query_result

    def stripe_delete_object(self, stripe_object_class, object_id):
        delete_result = self.stripe_call(stripe_object_class.delete, object_id)

        return delete_result

    def stripe_get_object(self, stripe_object_class, object_id):
        stripe_object = self.stripe_call(stripe_object_class.retreive, object_id)

        return stripe_object


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
            'metadata': {'site': offer.site.pk}

        }

    def build_price(self, offer, price):
        if 'stripe' not in offer.meta or 'product_id' not in offer.meta['stripe']:
            raise TypeError(f"Price cannot be created without a product_id on offer.meta['stripe'] field")

        price_data = {
            'product': offer.meta['stripe']['product_id'],
            'currency': price.currency,
            'unit_amount': self.convert_decimal_to_integer(price.cost),
            'metadata': {'site': offer.site.pk}
        }
        
        if offer.terms < TermType.PERPETUAL:
            price_data['recurring'] = {
                'interval': 'month' if offer.term_details['term_units'] == TermDetailUnits.MONTH else 'year',
                'interval_count': offer.term_details['payment_occurrences'],
                'usage_type': 'license'
            }
        
        return price_data
    
    def build_coupon(self, offer, price):
        coupon_data = {
            'name': offer.name,
            'currency': price.currency,
            'amount_off': self.convert_decimal_to_integer(offer.discount()),
            'metadata': {'site': offer.site.pk}
        }

        if offer.terms < TermType.PERPETUAL:
            coupon_data['duration']: 'once' if offer.term_details['trial_occurrences'] <= 1 else 'repeating'
            coupon_data['duration_in_months']: None if offer.term_details['trial_occurrences'] <= 1 else 'repeating'
        
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
    
    def build_subscription(self, customer_id, items, payment_id, offer):
        subscription_data = {
            'customer': customer_id,
            'items': [{'price': item.id} for item in items],
            'default_payment_method': payment_id,
            'trial_period_days': None if offer.term_details['trial_days'] < 1 else offer.term_details['trial_days'],
            'metadata': {'site': offer.site.pk}

        }

        subscription = self.stripe_create_object(self.stripe.Subscription, subscription_data)
        
        return subscription

    def sync_stripe_vendor_objects(self, site, customer_profile):
        offer_save_needed = False

        # Check if meta has this profile stripe customer and add if not
        if not customer_profile.meta.get('stripe_id'):
            customer = self.build_customer(customer_profile)
            customer_profile.meta['stripe_id'] = customer['id']
            customer_profile.save()

        for offer in Offer.objects.filter(site=site):
            meta = offer.meta
            # Check if meta has this offer stripe product and add if not
            if not meta.get('stripe', {}).get('product_id', {}):
                offer_save_needed = True
                product = self.build_product(offer)
                if meta.get('stripe', None):
                    meta['stripe']['product_id'] = product['id']
                else:
                    meta['stripe'] = {'product_id': product['id']}

            # Check if meta has this offer stripe price and add if not
            if not meta.get('stripe', {}).get('price_id', {}):
                offer_save_needed = True
                price = self.build_price(offer, offer.current_price_object())
                if meta.get('stripe', None):
                    meta['stripe']['price_id'] = price['id']
                else:
                    meta['stripe'] = {'price_id': price['id']}

            # Check if meta has this offer stripe coupon and add if not
            if not meta.get('stripe', {}).get('coupon_id', {}):
                offer_save_needed = True
                coupon = self.build_coupon(offer, offer.current_price_object())
                if meta.get('stripe', None):
                    meta['stripe']['coupon_id'] = coupon['id']
                else:
                    meta['stripe'] = {'coupon_id': coupon['id']}

            if offer_save_needed:
                offer.save()

    
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
            product_name_full = f'{product_name} - site {self.site.pk}'
            product_details = subscription.offer.term_details
            total = self.to_valid_decimal(subscription.total - subscription.discounts)
            interval = "month" if product_details['term_units'] == TermDetailUnits.MONTH else "year"
            status, product_response = self.check_product_does_exist(product_name_full)
            if status and product_response:
                existing_product_status, product_id = self.get_product_id_with_name(product_name_full)

                # Each product needs an attached price obj. Check if one exists for the product
                # and attach it to the mapping or create one and attach
                if existing_product_status and product_id:
                    existing_price_status, price_response = self.check_price_does_exist(product_id)
                    if existing_price_status and price_response:
                        new_price_status, price_id = self.get_price_id_with_product(product_id)
                    else:
                        new_price_status, price_id = self.create_price_with_product(product_id)

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
                    existing_price_status, price_response = self.check_price_does_exist(product_id)
                    if existing_price_status and product_response:
                        new_price_status, price_id = self.get_price_id_with_product(product_id)
                    else:
                        new_price_status, price_id = self.create_price_with_product(product_id)

                    self.products_mapping[product_name] = {
                        'product_id': product_id,
                        'price_id': price_id
                    }

    def build_search_query(self, params):
        """
        TODO unit test this
        TODO search is limited to name, metadata, and product. Expand if needed
        All search methods for all resources are here https://stripe.com/docs/search


        List of search values and their Stripe field types to build out search query
        [{
            'key_name': 'name',
            'key_value': 'product123',
            'field_type': 'name'
        },
        {
            'key_name': 'site',
            'key_value': 'site4',
            'field_type': 'metadata'
        },
        ]


        """
        if not isinstance(params, list):
            logger.info(f'Passed in params {params} is not a list of dicts')
            return None

        if not len(params) > 0:
            logger.info(f'Passed in params {params} cannot be empty')
            return None

        query = ""
        count = 0
        for query_obj in params:
            key = query_obj['key_name']
            value = query_obj['key_value']
            field = query_obj['field_type']
            if count != 0:
                if field == 'name':
                    query = f'{query} AND {key}~"{value}"'
                elif field == 'metadata':
                    query = f'{query} AND metadata["{key}"]: "{value}"'
                elif field == 'product':
                    query = f'{query} AND {key}:"{value}"'
            else:
                if field == 'name':
                    query = f'{key}~"{value}"'
                elif field == 'metadata':
                    query = f'metadata["{key}"]: "{value}"'
                elif field == 'product':
                    query = f'{key}:"{value}"'
            count += 1

        return query

    def check_product_does_exist(self, name, metadata=None):
        search = [{
            'key_name': 'name',
            'key_value': name,
            'field_type': 'name'
        }]
        if metadata:
            search.append({
                'key_name': metadata['key_name'],
                'key_value': metadata['key_value'],
                'field_type': 'metadata'
            })

        query = self.build_search_query(search)
        search_data = self.stripe_query_object(self.stripe.Product, {'query': query})
        if search_data:
            return True, search_data['data']
        return False, None

    def get_product_id_with_name(self, name, metadata=None):
        search = [{
            'key_name': 'name',
            'key_value': name,
            'field_type': 'name'
        }]
        if metadata:
            search.append({
                'key_name': metadata['key_name'],
                'key_value': metadata['key_value'],
                'field_type': 'metadata'
            })

        query = self.build_search_query(search)

        search_data = self.stripe_query_object(self.stripe.Product, {'query': query})
        if search_data:
            return True, search_data['data'][0]['id']
        return False, None

    def check_price_does_exist(self, product, metadata=None):
        search = [{
            'key_name': 'product',
            'key_value': product,
            'field_type': 'product'
        }]
        if metadata:
            search.append({
                'key_name': metadata['key_name'],
                'key_value': metadata['key_value'],
                'field_type': 'metadata'
            })

        query = self.build_search_query(search)
        search_data = self.stripe_query_object(self.stripe.Price, {'query': query})
        if search_data:
            return True, search_data['data']
        return False, None

    def get_price_id_with_product(self, product):
        price = self.stripe_get_object(self.stripe.Price, {'id': product})
        if price:
            return True, price['id']
        return False, None

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


    def process_payment_transaction_response(self):
        """
        Processes the transaction response from the stripe so it can be saved in the payment model
        """
        self.transaction_id = self.charge['id']
        self.transaction_response = {'raw': str(self.charge)}

    ##########
    # Base Processor Transaction Implementations
    ##########
    def pre_authorization(self):
        """
        Called before the authorization begins.
        """
        pass

    def process_payment(self):
        self.transaction_submitted = False
        self.charge = self.create_charge()
        if self.charge and self.charge["captured"]:
            self.transaction_submitted = True
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = '201'
            self.transaction_message[self.TRANSACTION_SUCCESS_MESSAGE] = "Success"
            self.payment.status = PurchaseStatus.CAPTURED
            self.payment.save()
            self.update_invoice_status(InvoiceStatus.COMPLETE)
            self.process_payment_transaction_response()

    def subscription_payment(self, subscription):
        payment_method_data = self.build_payment_method()
        stripe_payment_method = self.stripe_create_object(self.stripe.PaymentMethod, payment_method_data)
        
        setup_intent_object = self.build_setup_intent(stripe_payment_method.id)
        stripe_setup_intent = self.stripe_create_object(self.stripe.SetupIntent, setup_intent_object)

        subscription_obj = self.build_subscription(subscription, stripe_payment_method.id)
        stripe_subscription = self.processor.stripe_create_object(self.processor.stripe.Subscription, subscription_obj)


