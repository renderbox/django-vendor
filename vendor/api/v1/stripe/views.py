import json
import stripe

from django.conf import settings
from django.http.response import HttpResponse
from django.db.models import TextChoices
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from vendor.integrations import StripeIntegration
from vendor.utils import get_site_from_request


class StripeEvents(TextChoices):
    INVOICE_PAID = 'invoice.paid', _('Invoice Paid')
    INVOICE_PAYMENT_FAILED = 'invoice.payment_failed', _('Invoice Payment Failed')

class StripeBaseAPI(View):

    def __init__(self, **kwargs):
        self.stripe_event = None  # Variable used to store the webhooks event data.

        super().__init__(**kwargs)

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def is_valid_post(self, site):
        try:
            credentials = StripeIntegration(site)

            if credentials.instance and credentials.instance.private_key:
                self.event = stripe.Event.construct_from(json.loads(self.request.body), credentials.instance.private_key)
            elif settings.STRIPE_PUBLIC_KEY:
                self.event = stripe.Event.construct_from(json.loads(self.request.body), settings.STRIPE_PUBLIC_KEY)
            else:
                return False
            
        except ValueError as exce:
            return False
        except Exception as exce:
            return False

        return True

class StripeSubscriptionPayment(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(self.request)

        if not self.is_valid_post(site):
            return HttpResponse(status=400)

        if self.event.type != StripeEvents.INVOICE_PAID and self.event.data.object.billing_reason != 'subscription_cycle':
            return HttpResponse(status=400)

        if self.event.data.object.billing_reason != 'subscription_cycle':
            return HttpResponse(status=400)

        return HttpResponse(status=200)

class StripeSubscriptionPaymentFailed(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(request)

        if not self.is_valid_post(site):
            return HttpResponse(status=400)

        if self.event.type != StripeEvents.INVOICE_PAYMENT_FAILED:
            return HttpResponse(status=400)

        return HttpResponse(status=200)


# invoice.paid:
## self.event.data.object.subscription
## self.event.data.object.status = 'paid'
## self.event.data.object.customer_email

# invoice.payment_succeded

# invoice.draft
## self.event.data.object.subscription
