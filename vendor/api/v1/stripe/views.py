import stripe

from django.conf import settings
from django.http.response import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from vendor.integrations import StripeIntegration
from vendor.utils import get_site_from_request


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
                self.event = stripe.Event.construct_from(json.loads(payload), credentials.instance.private_key)
            elif settings.STRIPE_PUBLIC_KEY:
                self.event = stripe.Event.construct_from(json.loads(payload), settings.STRIPE_PUBLIC_KEY)
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

        return HttpResponse(status=200)