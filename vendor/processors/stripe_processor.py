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
        

    ##########
    # CRUD Stripe Object
    ##########
    def stipe_create_object(self, stripe_object_class, object_data):
        stripe_object = self.stripe_call(stripe_object_class.create, object_data)

        return stripe_object

    def stripe_query_object(self, stripe_object_class, query):
        query_result = self.stripe_call(stripe_object_class.search, query)

        return query_result

    def stripe_delete_object(self, stripe_object_class, object_id):
        delete_result = self.stripe_call(stripe_object_class.delete, object_id)

        return delete_result
    # def create_customer(self):
    #     # If current user doesnt have a customer id stripe object, create one
    #     # TODO save this customer id on user/profile for later use

    #     customer = self.stripe_call(self.stripe.Customer.create,{
    #         'name': self.invoice.profile.user.get_full_name(),
    #         'email': self.invoice.profile.user.email,
    #         'metadata': {
    #             'pk': self.invoice.profile.user.pk
    #         }
    #     })
    #     if customer:
    #         return True, customer
    #     return False, None
    def build_customer(self, customer_profile):
        customer_data = {
            'name': f"{customer_profile.user.first_name} {customer_profile.user.last_name}",
            'email': customer_profile.user.email,
            'metadata': {'site': customer_profile.site}
        }
        
        customer = self.stipe_create_object(self.stripe.Customer, customer_data)
        
        return customer
    
    def build_product(self, offer):
        product_data = {
            'name': offer.name,
            'metadata': {'site': instance.site}
        }

        product = self.stripe_create_object(self.stripe.Product, product_data)
        
        return product
    # def create_price_with_product(self, product):
        # price = self.stripe_call(self.stripe.Price.create, {
        #     'currency': self.invoice.currency,
        #     'product': product
        # })

        # if price:
        #     return True, price['id']
        # return False, None
    def build_price(self, offer, price):
        price_data = {
            'currency': price.currency,
            'unit_amount': price.cost,
            'metadata': {'site': instance.site}
        }
        if offer.terms < TermType.PERPETUAL:
            price_data['recurring'] = {
                'interval': 'month' if offer.term_details['term_units'] == TermDetailUnits.MONTH else 'year',
                'interval_count': offer.term_details['payment_occurrences'],
                'usage_type': 'license'
            }
        price = self.stripe_create_object(self.stripe.Price, price_data)
        
        return price
    
    def build_coupon(self, offer, price):
        coupon_data = {
            'name': offer.name,
            'currency': price.currency,
            'amount_off': offer.discount,
            'metadata': {'site': instance.site}
        }

        if offer.terms < TermType.PERPETUAL:
            coupon_data['duration']: 'once' if offer.term_details['trial_occurrences'] <= 1 else 'repeating'
            coupon_data['duration_in_months']: None if offer.term_details['trial_occurrences'] <= 1 else 'repeating'

        coupon = self.stripe_call(self.stripe.Coupon, coupon_data)
        
        return coupon
    
    # def create_subscription(self, offer, clients_customer, our_customer, application_fee=30.00):
    #     """
    #     Subscription pricing will be created in stripe dashboard
    #     """
    #     subscription = self.stripe_call(self.stripe.Subscription.create, {
    #         'customer': clients_customer,
    #         'currency': self.invoice.currency,
    #         'items': [
    #             {'price': self.products_mapping[offer.name]['price_id']}
    #         ],
    #         'expand': ["latest_invoice.payment_intent"],
    #         'transfer_data': {'destination': our_customer},
    #         'application_fee': application_fee,
    #         'payment_behavior': 'error_if_incomplete',
    #         'trial_period_days': offer.get_trial_days()
    #     })
    #     if subscription:
    #         return True, subscription
    #     return False, None
    def build_subscription(self, customer_id, items, payment_id, offer):
        subscription_data = {
            'customer': customer_id,
            'items':[{'price': item_id} for item in items],
            'default_payment_method': payment_id,
            'trial_period_days': None if offer.term_details['trial_days'] < 1 else offer.term_details['trial_days'],
            'metadata': {'site': instance.site}
        }

        subscription = self.stripe_create_object(self.stripe.Subscription, subscription_data)
        
        return subscription
    # def create_card_token(self, card):
        # token = self.stripe_call(self.stripe.Token.create, {
        #     'card': card
        # })
        # if token:
        #     return True, token
        # return False, None
    
    def create_setup_intent(self, setup_intent_data):
        setup_intent = self.stripe_call(self.stripe.SetupIntent.create, setup_intent_data)
        
        return setup_intent

    # def set_stripe_payment_source(self):
    #     if not self.source:
    #         if self.payment_info.is_valid():
    #             card_number = self.payment_info.cleaned_data.get('card_number')
    #             exp_month = self.payment_info.cleaned_data.get('expire_month')
    #             exp_year = self.payment_info.cleaned_data.get('expire_year')
    #             cvc = self.payment_info.cleaned_data.get('cvc_number')
    #             card = {
    #                'number': card_number,
    #                'exp_month': exp_month,
    #                'exp_year': exp_year,
    #                'cvc': cvc
    #             }
    #             status, card = self.create_card_token(card)
    #             if status and card:
    #                 self.source = card['id']
    def create_payment_method(self, payment_method_data):
        payment_method = self.stripe_call(self.stripe.PaymentMethod.create, payment_method_data)
        
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


    def check_product_does_exist(self, name):
        search_data = self.stripe_call(self.stripe.Product.search, {'query': f'name~"{name}"'})
        if search_data:
            return True, search_data['data']
        return False, None

    def get_product_id_with_name(self, name):
        search_data = self.stripe_call(self.stripe.Product.search, {'query': f'name~"{name}"'})
        if search_data:
            return True, search_data['data'][0]['id']
        return False, None

    def check_price_does_exist(self, product):
        search_data = self.stripe_call(self.stripe.Product.search, {'query': f'product:"{product}"'})
        if search_data:
            return True, search_data['data']
        return False, None

    def get_price_id_with_product(self, product):
        price = self.stripe_call(self.stripe.Price.retrieve, {'id': product})
        if price:
            return True, price['id']
        return False, None

    def create_charge(self):
        if self.source:
            charge = self.stripe_call(self.stripe.Charge.create, {
                'amount': self.to_stripe_valid_unit(self.invoice.get_one_time_transaction_total()),
                'currency': self.invoice.currency,
                'source': self.source,
            })
            if charge:
                return True, charge
        return False, None

    def create_payment_intent(self, customer):
        # Will return client secret value to be returned to the front end to continue processing payment
        # TODO do something with result error strings below

        intent = self.stripe_call(self.stripe.PaymentIntent.create, {
            'customer': customer['id'],
            'setup_future_usage': 'off_session',
            'amount': self.invoice.get_one_time_transaction_total(),
            'currency': self.invoice.currency,
            'automatic_payment_methods': {
                'enabled': True
            }
        })
        if intent:
            return True, intent.client_secret
        return False, None

    def process_payment_transaction_response(self):
        """
        Processes the transaction response from the stripe so it can be saved in the payment model
        """
        self.transaction_id = self.charge['id']
        self.transaction_response = {'raw': str(self.charge)}


    def process_payment(self):
        self.transaction_submitted = False
        charge_status, charge = self.create_charge()
        self.charge = charge
        if charge_status and charge["captured"]:
            self.transaction_submitted = True
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = '201'
            self.transaction_message[self.TRANSACTION_SUCCESS_MESSAGE] = "Success"
            self.payment.status = PurchaseStatus.CAPTURED
            self.payment.save()
            self.update_invoice_status(InvoiceStatus.COMPLETE)
            self.process_payment_transaction_response()

