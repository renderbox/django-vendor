import json
import logging
import stripe

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import HttpResponse
from django.db.models import TextChoices
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from vendor.models.choice import InvoiceStatus
from vendor.integrations import StripeIntegration
from vendor.utils import get_site_from_request
from vendor.models import CustomerProfile, Subscription, Invoice
from vendor.processors import StripeProcessor


logger = logging.getLogger(__name__)


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
    
    def is_incoming_event_correct(self, event, desired_event):
        if event.type != desired_event:
            return False

        # This check is recuired to make sure that the event is related to a subscription.
        if self.event.data.object.billing_reason != 'subscription_cycle':
            return False

        return True


class StripeSubscriptionInvoicePaid(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(self.request)

        if not self.is_valid_post(site):
            return HttpResponse(status=400)

        if not self.is_incoming_event_correct(self.event, StripeEvents.INVOICE_PAID):
            return HttpResponse(status=400)

        # TODO nice to move this assignments inside a generic function in the StripeBaseAPI class
        stripe_subscription_id = self.event.data.object.subscription
        stripe_customer_id = self.event.data.object.customer
        stripe_customer_email = self.event.data.object.customer_email
        stripe_transaction_id = self.event.data.object.charge
        stripe_invoice_id = self.event.data.object.stripe_id
        paid_date = timezone.datetime.fromtimestamp(self.event.data.object.status_transitions.paid_at)
        amount_paid = str(self.event.data.object.total)

    # TODO nice to move this try/except blocks inside a generic function in the StripeBaseAPI class
        try:
            customer_profile = CustomerProfile.objects.get(site=site, user__email__iequals=stripe_customer_email)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionInvoicePaid error: email: {stripe_customer_email} does not exits")
            return HttpResponse(status=400)

        if 'stripe_id' not in customer_profile.meta:
            customer_profile.meta['stripe_id'] = stripe_customer_id
            customer_profile.save()

        try:
            subscription = Subscription.objects.get(meta__stripe_id=stripe_subscription_id, profile=customer_profile)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionInvoicePaid customer: {customer_profile} does not have a subscription with stripe_id: {stripe_subscription_id}")
            return HttpResponse(status=400)

        offer = subscription.get_offer()

        if not offer:
            logger.error(f"StripeSubscriptionInvoicePaid {subscription} has no offer attached")
            return HttpResponse(status=400)

        invoice = Invoice.objects.create(
            profile=customer_profile,
            site=site,
            ordered_date=paid_date,
            total=float(f"{amount_paid[:-2]}.{amount_paid[-2:]}"),
            status=InvoiceStatus.COMPLETE
        )
        invoice.add_offer(offer)
        invoice.vendor_notes = {'stripe_id': stripe_invoice_id}
        invoice.save()

        processor = StripeProcessor(site, invoice)
        processor.renew_subscription(subscription, stripe_transaction_id, PurchaseStatus.SETTLED, payment_success=True)

        return HttpResponse(status=200)

class StripeSubscriptionPaymentFailed(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(request)

        if not self.is_valid_post(site):
            return HttpResponse(status=400)

        if not self.is_incoming_event_correct(self.event, StripeEvents.INVOICE_PAYMENT_FAILED):
            return HttpResponse(status=400)

        # TODO nice to move this assignments inside a generic function in the StripeBaseAPI class
        stripe_subscription_id = self.event.data.object.subscription
        stripe_customer_id = self.event.data.object.customer
        stripe_customer_email = self.event.data.object.customer_email
        stripe_transaction_id = self.event.data.object.charge
        stripe_invoice_id = self.event.data.object.stripe_id
        paid_date = timezone.datetime.fromtimestamp(self.event.data.object.status_transitions.paid_at)

        # TODO nice to move this try/except blocks inside a generic function in the StripeBaseAPI class
        try:
            customer_profile = CustomerProfile.objects.get(site=site, user__email__iequals=stripe_customer_email)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionInvoicePaid error: email: {stripe_customer_email} does not exits")
            return HttpResponse(status=400)

        if 'stripe_id' not in customer_profile.meta:
            customer_profile.meta['stripe_id'] = stripe_customer_id
            customer_profile.save()

        try:
            subscription = Subscription.objects.get(meta__stripe_id=stripe_subscription_id, profile=customer_profile)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionInvoicePaid customer: {customer_profile} does not have a subscription with stripe_id: {stripe_subscription_id}")
            return HttpResponse(status=400)

        offer = subscription.get_offer()

        if not offer:
            logger.error(f"StripeSubscriptionInvoicePaid {subscription} has no offer attached")
            return HttpResponse(status=400)

        invoice = Invoice.objects.create(
            profile=subscription.profile,
            site=subscription.profile.site,
            ordered_date=paid_date,
            status=InvoiceStatus.COMPLETE
        )

        invoice.add_offer(offer)
        invoice.vendor_notes = {}
        invoice.vendor_notes['stripe_id'] = stripe_invoice_id
        invoice.save()

        processor = StripeProcessor(site, invoice)
        processor.subscription_payment_failed(subscription, stripe_transaction_id)

        return HttpResponse(status=200)


class StripeSyncObjects(View):

    def get(self, request, *args, **kwargs):
        site = get_site_from_request(request)

        processor = StripeProcessor(site)
        processor.sync_stripe_vendor_objects(site)

        return HttpResponse(status=200)
