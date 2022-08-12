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

class StripeProcessor(PaymentProcessorBase):
    """
    Implementation of Stripe SDK
    https://stripe.com/docs/api/authentication?lang=python
    """

    def processor_setup(self, site):
        self.credentials = StripeIntegration(site)

        if self.credentials.instance:
            stripe.api_key = self.credentials.instance.private_key
        elif settings.STRIPE_API_KEY:
            stripe.api_key = settings.STRIPE_API_KEY
        else:
            logger.error("StripeProcessor missing keys in settings: STRIPE_API_KEY")
            raise ValueError("StripeProcessor missing keys in settings: STRIPE_API_KEY")

        self.init_transaction_types()

    def init_transaction_types(self):
        self.transaction_types = {
            TransactionTypes.AUTHORIZE: self.AUTHORIZE,
            TransactionTypes.CAPTURE: self.CAPTURE,
            TransactionTypes.REFUND: self.REFUND,
            TransactionTypes.VOID: self.VOID,
        }

    def create_charge(self, source):
        # TODO do something with result error strings below
        # TODO integrate vendor.models.Payment
        try:
            charge = stripe.Charge.create(
                amount=self.invoice.total,
                currency=self.invoice.currency,
                source=source,
                customer=self.invoice.profile.user.pk
            )
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught

            print('Status is: %s' % e.http_status)
            print('Code is: %s' % e.code)
            # param is '' in this case
            print('Param is: %s' % e.param)
            print('Message is: %s' % e.user_message)
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            result = '{"message":"Rate Limit Error"}'

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            result = '{"message":"Invalid Parameters"}'

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            result = '{"message":"Not Authenticated"}'

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            result = '{"message":"Network Error"}'

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            result = '{"message":"Something Went Wrong.  You were not charged, please try again."}'

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            # TODO: Send email to self
            result = '{"message":"A serious error has occured.  Our team has been notified."}'

        return charge

    def create_customer(self):
        # If current user doesnt have a customer id stripe object, create one
        # TODO do something with result error strings below
        # TODO save this customer id on user/profile for later use

        try:
            customer = stripe.Customer.create(
                name=self.invoice.profile.user.get_full_name(),
                email=self.invoice.profile.user.email,
                metadata={'pk': self.invoice.profile.user.pk}
            )

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            result = '{"message":"Rate Limit Error"}'

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            result = '{"message":"Invalid Parameters"}'

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            result = '{"message":"Not Authenticated"}'

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            result = '{"message":"Network Error"}'

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            result = '{"message":"Something Went Wrong.  You were not charged, please try again."}'

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            # TODO: Send email to self
            result = '{"message":"A serious error has occured.  Our team has been notified."}'

        return customer

    def create_payment_intent(self, customer):
        # Will return client secret value to be returned to the front end to continue processing payment
        # TODO do something with result error strings below

        try:
            intent = stripe.PaymentIntent.create(
                customer=customer['id'],
                setup_future_usage='off_session',
                amount=self.invoice.total,
                currency=self.invoice.currency,
                automatic_payment_methods={
                    'enabled': True,
                },
            )

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught

            print('Status is: %s' % e.http_status)
            print('Code is: %s' % e.code)
            # param is '' in this case
            print('Param is: %s' % e.param)
            print('Message is: %s' % e.user_message)

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            result = '{"message":"Rate Limit Error"}'

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            result = '{"message":"Invalid Parameters"}'

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            result = '{"message":"Not Authenticated"}'

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            result = '{"message":"Network Error"}'

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            result = '{"message":"Something Went Wrong.  You were not charged, please try again."}'

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            # TODO: Send email to self
            result = '{"message":"A serious error has occured.  Our team has been notified."}'

        return intent.client_secret