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

    def stripe_update_object(self, stripe_object_class, object_id, object_data):
        stripe_object = self.stripe_call(stripe_object_class.modify, object_id, **object_data)

        return stripe_object

    def stripe_list_objects(self, stripe_object_class, limit=10, starting_after=None):
        stripe_objects = self.stripe_call(stripe_object_class.list, limit=limit, starting_after=None)

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

        price_data = {
            'product': offer.meta['stripe']['product_id'],
            'currency': price.currency,
            'unit_amount': self.convert_decimal_to_integer(price.cost),
            'metadata': {'site': offer.site.domain, 'pk': price.pk}
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
        query = self.build_search_query([{
            'key_name': 'site',
            'key_value': site.domain,
            'field_type': 'metadata'
        }])
        customer_search = self.stripe_query_object(self.stripe.Customer, {'query': query})

        if customer_search:
            return customer_search['data']

        return None

    def get_stripe_customers_in_vendor(self, customer_email_list, site):
        """
        Returns all vendor customers who have been created as Stripe customers
        """
        users = CustomerProfile.objects.filter(
            user__email__iregex=r'(' + '|'.join(customer_email_list) + ')',  # iregex used for case insensitive list match
            site=site
        )

        return users

    def get_stripe_customers_not_in_vendor(self, customer_email_list, site):
        """
        Returns all vendor customers who have not been created as Stripe customers
        """
        users = CustomerProfile.objects.exclude(
            user__email__iregex=r'(' + '|'.join(customer_email_list) + ')',  # iregex used for case insensitive list match
            site=site
        )

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
            customer_id = profile.meta['id']
            profile_data = self.build_customer(profile)
            existing_stripe_customer = self.stripe_update_object(self.stripe.Customer, customer_id, profile_data)

            if existing_stripe_customer:
                profile.meta['stripe_id'] = existing_stripe_customer['id']
                profile.save()

    def sync_customers(self, site):
        stripe_customers = self.get_stripe_customers(site)
        stripe_customers_emails = [customer_obj['email'] for customer_obj in stripe_customers]
        stripe_customers_in_vendor = self.get_stripe_customers_in_vendor(stripe_customers_emails)
        stripe_customers_not_in_vendor = self.get_stripe_customers_not_in_vendor(stripe_customers_emails)

        self.create_stripe_customers(stripe_customers_not_in_vendor)
        self.update_stripe_customers(stripe_customers_in_vendor)

    def get_site_offers(self, site):
        """
        Returns all Stripe created Products
        """
        query = self.build_search_query([{
            'key_name': 'site',
            'key_value': site.domain,
            'field_type': 'metadata'
        }])
        product_search = self.stripe_query_object(self.stripe.Product, {'query': query})

        if product_search:
            return product_search['data']

        return None

    def get_price_with_pk(self, price_pk):
        """
        Returns stripe Price based on metadata pk value
        """
        query = self.build_search_query([{
            'key_name': 'pk',
            'key_value': price_pk,
            'field_type': 'metadata'
        }])
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

    def get_coupons(self, offer):
        """
        Returns the matching stripe Coupons on Offer by iterating all coupons
        and matching on site, amount_off, and duration_in_months.

        This is needed since there is no search method on Coupon. Will make multiple stripe calls until the
        list is exhausted
        """
        coupon_matches = []
        starting_after = None
        while 1:
            coupons = self.stripe_list_objects(self.stripe.Coupon, limit=100, starting_after=starting_after)
            matches = self.match_coupons(coupons, offer)
            coupon_matches.extend(matches)
            if coupons['has_more']:
                starting_after = coupons['data'][-1]['id']
            else:
                break

        return coupon_matches

    def get_offers_in_vendor(self, offer_pk_list, site):
        offers = Offer.objects.filter(site=site, pk__in=offer_pk_list)
        return offers

    def get_offers_not_in_vendor(self, offer_pk_list, site):
        offers = Offer.objects.exclude(site=site, pk__in=offer_pk_list)
        return offers

    def create_offers(self, offers):
        for offer in offers:
            product_data = self.build_product(offer)
            price_data = self.build_price(offer, offer.current_price_object())
            coupon_data = self.build_coupon(offer, offer.current_price_object())

            new_stripe_product = self.stripe_create_object(self.stripe.Product, product_data)
            new_stripe_price = self.stripe_create_object(self.stripe.Price, price_data)
            new_stripe_coupon = self.stripe_create_object(self.stripe.Coupon, coupon_data)

            if new_stripe_product:
                if offer.meta.get('stripe'):
                    offer.meta['stripe']['product_id'] = new_stripe_product['id']
                else:
                    offer.meta['stripe'] = {'product_id': new_stripe_product['id']}

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

            # If this offer has a discount check if its on stripe to create, update, delete
            if discount:
                stripe_coupon_matches = self.get_coupons(offer)

                if not stripe_coupon_matches:
                    stripe_coupon = self.stripe_create_object(self.stripe.Coupon, coupon_data)
                elif len(stripe_coupon_matches) == 1:
                    coupon_id = stripe_coupon_matches[0]['id']
                    stripe_coupon = self.stripe_update_object(self.stripe.Coupon, coupon_id, coupon_data)
                else:
                    # TODO what to do for multiple coupon matches?
                    pass

                if offer.meta.get('stripe'):
                    offer.meta['stripe']['coupon_id'] = stripe_coupon['id']
                else:
                    offer.meta['stripe'] = {'coupon_id': stripe_coupon['id']}

            offer.save()

    def sync_offers(self, site):
        products = self.get_site_offers(site)
        offer_pk_list = [product['metadata']['pk'] for product in products]
        offers_in_vendor = self.get_offers_in_vendor(offer_pk_list, site)
        offers_not_in_vendor = self.get_offers_not_in_vendor(offer_pk_list, site)

        self.create_offers(offers_not_in_vendor)
        self.update_offers(offers_in_vendor)

    def sync_stripe_vendor_objects(self):
        """
        Sync up all the CustomerProfiles, Offers, Prices, and Coupons for all of the sites
        """
        for site in Site.objects.all():
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


