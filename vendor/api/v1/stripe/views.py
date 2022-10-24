import stripe

from django.views import View
from django.views.decorators.edit import csrf_exempt

from vendor.integrations import StripeIntegration


class StripeBaseAPI(View):

    def __init__(self, **kwargs):
        self.stripe_event = None  # Variable used to store the webhooks event data.

        super().__init__(**kwargs)

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def is_valid_post(self, site):
        try:
            self.credentials = StripeIntegration(site)

            if self.credentials.instance.private_key:
                self.event = stripe.Event.construct_from(json.loads(payload), self.credentials.instance.private_key)
            elif settings.STRIPE_PUBLIC_KEY:
                self.event = stripe.Event.construct_from(json.loads(payload), settings.STRIPE_PUBLIC_KEY)
            else:
                return False
            
        except ValueError as exce:
            return False
        except Exception as exce:
            return False

        return True