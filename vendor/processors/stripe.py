"""
Payment processor for Stripe.
"""
from django.conf import settings

import stripe

from .base import PaymentProcessorBase


class StripeProcessor(PaymentProcessorBase):

    def processor_setup(self):
        stripe.api_key = settings.STRIPE_TEST_PUBLIC_KEY    # TODO: This should work, but may not the best way to do this

    def get_checkout_context(self, request=request, context={}):
        '''
        The Invoice plus any additional values to include in the payment record.
        '''
        context = super().get_checkout_context(request=request, context=context)
        context['integration_check'] = 'accept_a_payment'

        metadata = {}
        metadata['integration_check'] = 'accept_a_payment'
        metadata['order_id'] = str(self.invoice.pk)

        intent = stripe.PaymentIntent.create(
            amount=int(self.invoice.total * 100),  # Amount in pennies so it can be an int() rather than a float
            currency=self.invoice.currency,        # "usd"
            metadata=metadata,
        )

        context['client_secret'] = intent.client_secret
        context['pub_key'] = settings.STRIPE_TEST_PUBLIC_KEY

        return context

    def process_payment(self, token):
        super().process_payment()
        payment = self.get_payment_model(self.invoice)

        try:
            # Use Stripe's library to make requests...
            # All necessary chage information should come from the invoice
            charge = stripe.Charge.create(
                amount = amount,
                currency = self.invoice.currency,
                source = self.transaction_token
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

