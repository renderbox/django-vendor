# Payment Processors
from django.conf import settings

import stripe

from .models import PurchaseStatus, Payment

class PaymentProcessorBase():
    '''
    Setup the core functionality for all processors.

    '''
    status = None

    def set_amount(self, amount):
        self.status = PurchaseStatus.QUEUED

    def process_payment(self, invoice):
        self.status = PurchaseStatus.ACTIVE
        # Returns a Payment model with a result


class DummyProcessor(PaymentProcessorBase):
    pass
    # def process_payment(self, invoice):


class StripeProcessor(PaymentProcessorBase):

    def __init__(self):
        stripe.api_key = settings.STRIPE_PUBLISHABLE_KEY    # TODO: This should work, but may not the best way to do this

    def process_payment(self, invoice, token):
        
        amount = invoice.get_amount()

        payment = Payment()
        payment.profile = invoice.profile
        payment.amount = amount
        payment.provider = "stripe"
        payment.invoice = invoice

        try:
            # Use Stripe's library to make requests...
            # All necessary chage information should come from the invoice
            charge = stripe.Charge.create(
                amount = amount,
                currency = invoice.currency
                source = token
            )

            payment.transaction = charge['id']
            payment.success = True

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught

            payment.result = e.json_body

            # err = payment.result.get('error', {})
            # from django.contrib import messages
            # print('Status is: %s' % e.http_status)
            # print('Type is: %s' % e.error.type)
            # print('Code is: %s' % e.error.code)
            # # param is '' in this case
            # print('Param is: %s' % e.error.param)
            # print('Message is: %s' % e.error.message)

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            # pass
            payment.result = '{"message":"Rate Limit Error"}'

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            payment.result = '{"message":"Invalid Parameters"}'

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            payment.result = '{"message":"Not Authenticated"}'

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            payment.result = '{"message":"Network Error"}'

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            payment.result = '{"message":"Something Went Wrong.  You were not charged, please try again."}'

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            # TODO: Send email to self
            payment.result = '{"message":"A serious error has occured.  Our team has been notified."}'

        payment.save()

        # TODO: Set Order Status
        # invoice.payment = payment
        # invoice.save()

        return payment
