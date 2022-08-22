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

    TRANSACTION_SUCCESS_MESSAGE = 'message'
    TRANSACTION_SUCCESS_CODE = 'code'
    TRANSACTION_FAIL_MESSAGE = 'error_text'
    TRANSACTION_FAIL_CODE = 'error_code'
    TRANSACTION_RESPONSE_CODE = 'response_code'
    transaction_submitted = False

    SUBSCRIPTION_TYPE_ANNUAL = 'annual'
    SUBSCRIPTION_TYPE_MONTHLY = 'monthly'

    # ex price_1LZfm72eZvKYlo2CTSzfbawl get the value from stripe dashboard
    SUBSCRIPTION_PLANS = {
        SUBSCRIPTION_TYPE_ANNUAL: settings.STRIPE_SUBSCRIPTION_ANNUAL,
        SUBSCRIPTION_TYPE_MONTHLY: settings.STRIPE_SUBSCRIPTION_MONTHLY
    }

    def get_checkout_context(self, request=None, context={}):
        context = super().get_checkout_context(context=context)
        # TODO need to figure out how we're building stripe form
        """if 'credit_card_form' not in context:
            context['credit_card_form'] = CreditCardForm(initial={'payment_type': PaymentTypes.CREDIT_CARD})
        if 'billing_address_form' not in context:
            context['billing_address_form'] = BillingAddressForm()"""
        return context

    def processor_setup(self, site, source=None):
        self.credentials = StripeIntegration(site)
        self.stripe_source = source
        if self.credentials.instance:
            stripe.api_key = self.credentials.instance.private_key
        elif settings.STRIPE_API_KEY:
            stripe.api_key = settings.STRIPE_PUBLIC_KEY
        else:
            logger.error("StripeProcessor missing keys in settings: STRIPE_PUBLIC_KEY")
            raise ValueError("StripeProcessor missing keys in settings: STRIPE_PUBLIC_KEY")

    def create_charge(self, source):
        # TODO integrate vendor.models.Payment
        try:
            charge = stripe.Charge.create(
                amount=self.invoice.get_one_time_transaction_total(),
                currency=self.invoice.currency,
                source=source,
                customer=self.invoice.profile.user.pk
            )
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = e.user_message
            return None
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Rate Limit Error"
            return None
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Invalid Parameters"
            return None
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Not Authenticated"
            return None
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Network Error"
            return None
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Something Went Wrong.  You were not charged, please try again."
            return None
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            # TODO: Send email to self
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "A serious error has occured.  Our team has been notified."
            return None

        self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = '201'
        self.transaction_message[self.TRANSACTION_SUCCESS_MESSAGE] = "Card was successfully charged"
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
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Rate Limit Error"
            return None

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Invalid Parameters"
            return None

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Not Authenticated"
            return None

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Network Error"
            return None

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Something Went Wrong.  You were not charged, please try again."
            return None

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            # TODO: Send email to self
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "A serious error has occured.  Our team has been notified."
            return None

        self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = '201'
        self.transaction_message[self.TRANSACTION_SUCCESS_MESSAGE] = "Success"
        return customer

    def create_payment_intent(self, customer):
        # Will return client secret value to be returned to the front end to continue processing payment
        # TODO do something with result error strings below

        try:
            intent = stripe.PaymentIntent.create(
                customer=customer['id'],
                setup_future_usage='off_session',
                amount=self.invoice.get_one_time_transaction_total(),
                currency=self.invoice.currency,
                automatic_payment_methods={
                    'enabled': True,
                },
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

        return intent.client_secret

    def create_subscription(self, customer, destination_customer, subscription_type=SUBSCRIPTION_TYPE_MONTHLY):
        """
        Subscription pricing will be created in stripe dashboard
        """
        try:
            price = self.SUBSCRIPTION_PLANS[self.SUBSCRIPTION_TYPE_MONTHLY] \
                if subscription_type == self.SUBSCRIPTION_TYPE_MONTHLY \
                else self.SUBSCRIPTION_PLANS[self.SUBSCRIPTION_TYPE_ANNUAL]
            stripe_subscription = stripe.Subscription.create(
                customer=customer,
                currency=self.invoice.currency,
                items=[
                    {"price": price}
                ],
                expand=["latest_invoice.payment_intent"],
                transfer_data={"destination": destination_customer},
                application_fee_percent=30.00
            )

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Rate Limit Error"
            return None

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Invalid Parameters"
            return None

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Not Authenticated"
            return None

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Network Error"
            return None

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "Something Went Wrong.  You were not charged, please try again."
            return None

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            # TODO: Send email to self
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = e.http_status
            self.transaction_message[self.TRANSACTION_FAIL_CODE] = e.code
            self.transaction_message[self.TRANSACTION_FAIL_MESSAGE] = "A serious error has occured.  Our team has been notified."
            return None

        self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = '201'
        self.transaction_message[self.TRANSACTION_SUCCESS_MESSAGE] = "Success"
        return stripe_subscription

    def process_payment(self):
        self.transaction_submitted = False
        charge = self.create_charge()
        if charge["captured"]:
            self.transaction_submitted = True
            self.transaction_message[self.TRANSACTION_RESPONSE_CODE] = '201'
            self.transaction_message[self.TRANSACTION_SUCCESS_MESSAGE] = "Success"
            self.payment.status = PurchaseStatus.CAPTURED


