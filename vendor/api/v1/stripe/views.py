import json
import logging
import stripe

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import HttpResponse
from django.db.models import TextChoices, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from vendor.models.choice import InvoiceStatus, PurchaseStatus
from vendor.integrations import StripeIntegration
from vendor.utils import get_site_from_request
from vendor.models import CustomerProfile, Subscription, Invoice
from vendor.processors import StripeProcessor
from vendor.config import SupportedPaymentProcessor


logger = logging.getLogger(__name__)



# TODO: Need to add more validation to function example:
# The lowest number can only 50 which transaltes to $0.50
# Probably should also added it to the processor as a static function
def convert_integer_to_float(number):
    number_string = str(number)

    return float(f"{number_string[:-2]}.{number_string[-2:]}")


class StripeEvents(TextChoices):
    INVOICE_PAID = 'invoice.paid', _('Invoice Paid')
    INVOICE_PAYMENT_FAILED = 'invoice.payment_failed', _('Invoice Payment Failed')
    INOVICE_PAYMENT_SUCCEEDED = 'invoice.payment_succeeded', _('Invoice Payment Succeeded')
    PAYMENT_INTENT_SUCCEDED = 'payment_intent.succeeded', _("Payment Succeeded")
    CHARGE_SUCCEEDED = 'charge.succeeded', _('Charge Succeeded')
    SOURCE_EXPIRED = 'customer.source.expired', _('Source Expired')



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
    
    def is_incoming_event_correct_and_recurring(self, event, desired_event):
        if event.type != desired_event:
            return False

        # This check is recuired to make sure that the event is related to a subscription.
        if self.event.data.object.billing_reason != 'subscription_cycle':
            return False

        return True
    
    def is_incoming_event_correct(self, event, desired_event):
        if event.type != desired_event:
            return False

        return True


class StripeSubscriptionInvoicePaid(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(self.request)

        if not self.is_valid_post(site):
            logger.error(f"StripeSubscriptionInvoicePaid error: invalid post")
            return HttpResponse(status=400, content="StripeSubscriptionInvoicePaid invalid post")

        if not self.is_incoming_event_correct_and_recurring(self.event, StripeEvents.INVOICE_PAID):
            logger.error(f"StripeSubscriptionInvoicePaid error: invalid event: {self.event}")
            return HttpResponse(status=400, content=f"StripeSubscriptionInvoicePaid error: invalid event: {self.event}")

        stripe_invoice = self.event.data.object
        paid_date = timezone.datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at)
        amount_paid = convert_integer_to_float(stripe_invoice.total)

        # TODO nice to move this try/except blocks inside a generic function in the StripeBaseAPI class
        try:
            customer_profile = CustomerProfile.objects.get(site=site, user__email=stripe_invoice.customer_email)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionInvoicePaid error: email: {stripe_invoice.customer_email} does not exist")
            return HttpResponse(status=400, content=f"StripeSubscriptionInvoicePaid error: email: {stripe_invoice.customer_email} does not exist")

        if 'stripe_id' not in customer_profile.meta:
            customer_profile.meta['stripe_id'] = stripe_invoice.customer
            customer_profile.save()

        try:
            subscription = Subscription.objects.get(meta__stripe_id=stripe_invoice.subscription, profile=customer_profile)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionInvoicePaid customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")
            return HttpResponse(status=400, content=f"StripeSubscriptionInvoicePaid customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")

        offer = subscription.get_offer()

        if not offer:
            logger.error(f"StripeSubscriptionInvoicePaid {subscription} has no offer attached")
            return HttpResponse(status=400, content=f"StripeSubscriptionInvoicePaid {subscription} has no offer attached")

        invoice = Invoice.objects.create(
            profile=customer_profile,
            site=site,
            ordered_date=paid_date,
            total=amount_paid,
            status=InvoiceStatus.COMPLETE
        )
        invoice.add_offer(offer)
        invoice.vendor_notes = {'stripe_id': stripe_invoice.stripe_id}
        invoice.save()

        processor = StripeProcessor(site, invoice)
        processor.renew_subscription(subscription, stripe_invoice.charge, PurchaseStatus.SETTLED, payment_success=True)

        return HttpResponse(status=200)


class StripeSubscriptionPaymentFailed(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(request)

        if not self.is_valid_post(site):
            logger.error("StripeSubscriptionPaymentFailed error: invalid post")
            return HttpResponse(status=400, content="StripeSubscriptionPaymentFailed error: invalid post")

        if not self.is_incoming_event_correct_and_recurring(self.event, StripeEvents.INVOICE_PAYMENT_FAILED):
            logger.error(f"StripeSubscriptionPaymentFailed error: invalid event: {self.event}")
            return HttpResponse(status=400, content=f"StripeSubscriptionPaymentFailed error: invalid event: {self.event}")

        stripe_invoice = self.event.data.object
        paid_date = timezone.datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at)

        # TODO nice to move this try/except blocks inside a generic function in the StripeBaseAPI class
        try:
            customer_profile = CustomerProfile.objects.get(site=site, user__email=stripe_invoice.customer_email)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionPaymentFailed error: email: {stripe_invoice.customer_email} does not exist")
            return HttpResponse(status=400, content=f"StripeSubscriptionPaymentFailed error: email: {stripe_invoice.customer_email} does not exist")

        if 'stripe_id' not in customer_profile.meta:
            customer_profile.meta['stripe_id'] = stripe_invoice.customer
            customer_profile.save()

        try:
            subscription = Subscription.objects.get(meta__stripe_id=stripe_invoice.subscription, profile=customer_profile)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionPaymentFailed customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")
            return HttpResponse(status=400, content=f"StripeSubscriptionPaymentFailed customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")

        offer = subscription.get_offer()

        if not offer:
            logger.error(f"StripeSubscriptionPaymentFailed {subscription} has no offer attached")
            return HttpResponse(status=400, content=f"StripeSubscriptionPaymentFailed {subscription} has no offer attached")

        invoice = Invoice.objects.create(
            profile=subscription.profile,
            site=subscription.profile.site,
            ordered_date=paid_date,
            status=InvoiceStatus.COMPLETE
        )

        invoice.add_offer(offer)
        invoice.vendor_notes = {}
        invoice.vendor_notes['stripe_id'] = stripe_invoice.stripe_id
        invoice.save()

        processor = StripeProcessor(site, invoice)
        processor.subscription_payment_failed(subscription, stripe_invoice.charge)

        return HttpResponse(status=200)


class StripeInvoicePaid(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(self.request)

        if not self.is_valid_post(site):
            logger.error("StripeInvoicePaid error: invalid post")
            return HttpResponse(status=400, content="StripeInvoicePaid error: invalid post")

        if not self.is_incoming_event_correct(self.event, StripeEvents.INOVICE_PAYMENT_SUCCEEDED):
            logger.error(f"StripeInvoicePaid error: invalid event {self.event}")
            return HttpResponse(status=400, content=f"StripeInvoicePaid error: invalid event {self.event}")

        stripe_invoice = self.event.data.object

        try:
            customer_profile = CustomerProfile.objects.get(site=site, user__email=stripe_invoice.customer_email)
        except ObjectDoesNotExist:
            logger.error(f"StripeInvoicePaid error: email: {stripe_invoice.customer_email} does not exist")
            return HttpResponse(status=400, content=f"StripeInvoicePaid error: email: {stripe_invoice.customer_email} does not exist")

        if 'stripe_id' not in customer_profile.meta:
            customer_profile.meta['stripe_id'] = stripe_invoice.customer
            customer_profile.save()

        try:
            subscription = Subscription.objects.get(gateway_id=stripe_invoice.subscription, profile=customer_profile)
        except ObjectDoesNotExist:
            logger.error(f"StripeInvoicePaid customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")
            return HttpResponse(status=400, content=f"StripeInvoicePaid customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")

        payment = subscription.payments.filter(Q(transaction="") | Q(transaction=None), status=PurchaseStatus.QUEUED).first()
        receipt = subscription.receipts.filter(Q(transaction="") | Q(transaction=None)).first()

        if not payment and not receipt:
            logger.warning(f"There are no payments to update for subscription: {subscription}. Stripe Invoice: {stripe_invoice.id}")
            return HttpResponse(status=400, content=f"There are no payments to update for subscription: {subscription}. Stripe Invoice: {stripe_invoice.id}")
        
        payment.transaction = stripe_invoice.charge
        payment.status = PurchaseStatus.SETTLED
        payment.save()

        receipt.transaction = stripe_invoice.charge
        receipt.save()

        return HttpResponse(status=200)


class StripeCardExpiring(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(self.request)

        if not self.is_valid_post(site):
            logger.error("StripeCardExpiring error: invalid event post")
            return HttpResponse(status=400, content="StripeCardExpiring error: invalid event post")

        if not self.is_incoming_event_correct(self.event, StripeEvents.SOURCE_EXPIRED):
            logger.error(f"StripeCardExpiring error: invalid event {self.event}")
            return HttpResponse(status=400, content=f"StripeCardExpiring error: invalid event {self.event}")

        stripe_card = self.event.data.object

        stripe_customer_id = stripe_card['customer']
        if stripe_customer_id:
            try:
                customer_profile = CustomerProfile.objects.get(meta__stripe_id=stripe_customer_id)
            except ObjectDoesNotExist:
                logger.error(f"StripeCardExpiring: stripe id {stripe_customer_id} does not exist for customer in vendor")
                return HttpResponse(status=200, content=f"StripeCardExpiring: stripe id {stripe_customer_id} does not exist for customer in vendor")

            email = customer_profile.user.email
            logger.info(f'StripeCardExpiring: sending customer_source_expiring signal for site {site} and email {email}')
            
            processor = StripeProcessor(site)
            processor.customer_card_expired(site, email)
            
        return HttpResponse(status=200)


class StripeSyncObjects(View):

    def get(self, request, *args, **kwargs):
        site = get_site_from_request(request)
        logger.info(f'StripeSyncObjects: started for site: {site}')

        processor = StripeProcessor(site)
        processor.sync_stripe_vendor_objects(site)

        logger.info(f'StripeSyncObjects: finished for site: {site}')
        return HttpResponse(status=200)

