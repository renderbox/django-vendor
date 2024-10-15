import json
import logging
import stripe

from django import dispatch
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


logger = logging.getLogger(__name__)




##########
# SIGNALS
stripe_invoice_upcoming = dispatch.Signal()


class StripeEvents(TextChoices):
    INVOICE_PAID = 'invoice.paid', _('Invoice Paid')
    INVOICE_PAYMENT_FAILED = 'invoice.payment_failed', _('Invoice Payment Failed')
    INOVICE_PAYMENT_SUCCEEDED = 'invoice.payment_succeeded', _('Invoice Payment Succeeded')
    INVOICE_UPCOMING = 'invoice.upcoming', _('Upcoming Invoice')
    PAYMENT_INTENT_SUCCEDED = 'payment_intent.succeeded', _("Payment Succeeded")
    CHARGE_SUCCEEDED = 'charge.succeeded', _('Charge Succeeded')
    SOURCE_EXPIRED = 'customer.source.expired', _('Source Expired')
    SUBSCRIPTION_TRIAL_END = 'customer.subscription.trial_will_end', _('Trial Period Will End')


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
            logger.error(f"Stripe Webhook ValueError exception: {exce}")
            return False
        except Exception as exce:
            logger.error(f"Stripe Webhook exception: {exce}")
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


# Warning StripeSubscriptionInvoicePaid will removed in favor of StripeInvoicePaymentSuccededEvent
class StripeSubscriptionInvoicePaid(StripeBaseAPI):
    
    def post(self, request, *args, **kwargs):
        stripe_invoice = self.event.data.object

        site = get_site_from_request(self.request)
        processor = StripeProcessor(site)

        if not self.is_valid_post(site):
            logger.error("StripeSubscriptionInvoicePaid error: invalid post")
            return HttpResponse(status=200, content="StripeSubscriptionInvoicePaid invalid post")

        if not self.is_incoming_event_correct_and_recurring(self.event, StripeEvents.INVOICE_PAID):
            logger.error(f"StripeSubscriptionInvoicePaid error: invalid event: {self.event}")
            return HttpResponse(status=200, content=f"StripeSubscriptionInvoicePaid error: invalid event: {self.event}")

        paid_date = timezone.datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at, tz=timezone.utc)
        stripe_charge = processor.stripe_get_object(processor.stripe.Charge, stripe_invoice.charge)

        customer_profile, stripe_customer = processor.get_customer_profile_and_stripe_customer(stripe_invoice.customer)

        if not customer_profile:
            logger.error(f"StripeSubscriptionInvoicePaid error: email: {stripe_invoice.customer_email} does not exist")
            return HttpResponse(status=200, content=f"StripeSubscriptionInvoicePaid error: email: {stripe_invoice.customer_email} does not exist")

        stripe_subscription = processor.stripe_get_object(processor.stripe.Subscription, stripe_invoice.subscription)
        subscription, created = processor.get_or_create_subscription_from_stripe_subscription(customer_profile, stripe_subscription)

        if created:
            processor.sync_stripe_subscription(site, stripe_subscription)
            msg = f"Synced Stripe Subscription: ({subscription.pk},{stripe_subscription.id}), customer: ({customer_profile.pk}, {stripe_customer.id}) site: {site}"
            logger.info(msg)
            return HttpResponse(status=200, content=msg)
        
        stripe_product = processor.stripe_get_object(processor.stripe.Product, stripe_subscription.plan.product)
        offer = processor.get_offer_from_stripe_product(stripe_product)

        if not offer:
            logger.error(f"StripeSubscriptionInvoicePaid {subscription} has no offer attached")
            return HttpResponse(status=200, content=f"StripeSubscriptionInvoicePaid {subscription} has no offer attached")

        payment_status = processor.get_payment_status(stripe_charge.status, stripe_charge.refunded)
        processor.invoice, created = processor.get_or_create_invoice_from_stripe_invoice(stripe_invoice, offer, customer_profile)
        processor.renew_subscription(subscription, stripe_invoice.charge, payment_status, payment_success=True, submitted_date=paid_date)

        return HttpResponse(status=200)


class StripeSubscriptionPaymentFailed(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(request)

        if not self.is_valid_post(site):
            logger.error("StripeSubscriptionPaymentFailed error: invalid post")
            return HttpResponse(status=200, content="StripeSubscriptionPaymentFailed error: invalid post")

        if not self.is_incoming_event_correct_and_recurring(self.event, StripeEvents.INVOICE_PAYMENT_FAILED):
            logger.error(f"StripeSubscriptionPaymentFailed error: invalid event: {self.event}")
            return HttpResponse(status=200, content=f"StripeSubscriptionPaymentFailed error: invalid event: {self.event}")

        stripe_invoice = self.event.data.object
        paid_date = timezone.datetime.fromtimestamp(stripe_invoice.effective_at, tz=timezone.utc)
        processor = StripeProcessor(site)

        customer_profile, stripe_customer = processor.get_customer_profile_and_stripe_customer(stripe_invoice.customer)
        if not customer_profile:
            logger.error(f"StripeSubscriptionPaymentFailed error: email: {stripe_invoice.customer_email} does not exist")
            return HttpResponse(status=200, content=f"StripeSubscriptionPaymentFailed error: email: {stripe_invoice.customer_email} does not exist")

        try:
            subscription = Subscription.objects.get(gateway_id=stripe_invoice.subscription, profile=customer_profile)
        except ObjectDoesNotExist:
            logger.error(f"StripeSubscriptionPaymentFailed customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")
            return HttpResponse(status=200, content=f"StripeSubscriptionPaymentFailed customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")

        offer = subscription.get_offer()

        if not offer:
            logger.error(f"StripeSubscriptionPaymentFailed {subscription} has no offer attached")
            return HttpResponse(status=200, content=f"StripeSubscriptionPaymentFailed {subscription} has no offer attached")

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
        processor.invoice = invoice
        processor.subscription_payment_failed(subscription, stripe_invoice.charge)

        return HttpResponse(status=200)


# Warning StripeInvoicePaid will removed in favor of StripeInvoicePaymentSuccededEvent
class StripeInvoicePaid(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(self.request)
        processor = StripeProcessor(site)

        if not self.is_valid_post(site):
            logger.error("StripeInvoicePaid error: invalid post")
            return HttpResponse(status=200, content="StripeInvoicePaid error: invalid post")

        if not self.is_incoming_event_correct(self.event, StripeEvents.INOVICE_PAYMENT_SUCCEEDED):
            logger.error(f"StripeInvoicePaid error: invalid event {self.event}")
            return HttpResponse(status=200, content=f"StripeInvoicePaid error: invalid event {self.event}")

        stripe_invoice = self.event.data.object

        customer_profile, stripe_customer = processor.get_customer_profile_and_stripe_customer(stripe_invoice.customer)

        try:
            customer_profile = CustomerProfile.objects.get(site=site, user__email=stripe_invoice.customer_email)
        except ObjectDoesNotExist:
            logger.error(f"StripeInvoicePaid error: email: {stripe_invoice.customer_email} does not exist")
            return HttpResponse(status=200, content=f"StripeInvoicePaid error: email: {stripe_invoice.customer_email} does not exist")

        if 'stripe_id' not in customer_profile.meta:
            customer_profile.meta['stripe_id'] = stripe_invoice.customer
            customer_profile.save()

        try:
            subscription = Subscription.objects.get(gateway_id=stripe_invoice.subscription, profile=customer_profile)
        except ObjectDoesNotExist:
            logger.error(f"StripeInvoicePaid customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")
            return HttpResponse(status=200, content=f"StripeInvoicePaid customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}")

        payment = subscription.payments.filter(Q(transaction="") | Q(transaction=None), status=PurchaseStatus.QUEUED).first()
        receipt = subscription.receipts.filter(Q(transaction="") | Q(transaction=None)).first()

        if not payment and not receipt:
            logger.warning(f"There are no payments to update for subscription: {subscription}. Stripe Invoice: {stripe_invoice.id}")
            return HttpResponse(status=200, content=f"There are no payments to update for subscription: {subscription}. Stripe Invoice: {stripe_invoice.id}")
        
        if payment:
            payment.transaction = stripe_invoice.charge
            payment.status = PurchaseStatus.SETTLED
            payment.save()

        if receipt:
            receipt.transaction = stripe_invoice.charge
            receipt.save()

        return HttpResponse(status=200)


class StripeCardExpiring(StripeBaseAPI):

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(self.request)

        if not self.is_valid_post(site):
            logger.error("StripeCardExpiring error: invalid event post")
            return HttpResponse(status=200, content="StripeCardExpiring error: invalid event post")

        if not self.is_incoming_event_correct(self.event, StripeEvents.SOURCE_EXPIRED):
            logger.error(f"StripeCardExpiring error: invalid event {self.event}")
            return HttpResponse(status=200, content=f"StripeCardExpiring error: invalid event {self.event}")

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


def process_stripe_invoice_line_items_payment_succeded(stripe_invoice, site):
    processor = StripeProcessor(site)

    customer_profile, stripe_customer = processor.get_customer_profile_and_stripe_customer(stripe_invoice.customer)

    stripe_charge = processor.stripe_get_object(processor.stripe.Charge, stripe_invoice.charge)
    stripe_payment_method = processor.stripe_get_object(processor.stripe.PaymentMethod, stripe_charge.payment_method)

    offers = processor.get_offers_from_invoice_line_items(stripe_invoice.lines['data'])

    for offer in offers:
        processor.invoice, created = processor.get_or_create_invoice_from_stripe_invoice(stripe_invoice, offer, customer_profile)

    payment = processor.get_or_create_payment_from_stripe_payment_and_charge(processor.invoice, stripe_payment_method, stripe_charge)

    if payment.status == PurchaseStatus.SETTLED:
        processor.create_single_purchase_receipts(processor.invoice, payment, stripe_charge)


def process_stripe_invoice_subscription_payment_succeded(stripe_invoice, site):
    processor = StripeProcessor(site)

    paid_date = timezone.datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at, tz=timezone.utc)
    payment_status = PurchaseStatus.SETTLED

    if stripe_invoice.charge:
        stripe_charge = processor.stripe_get_object(processor.stripe.Charge, stripe_invoice.charge)
        payment_status = processor.get_payment_status(stripe_charge.status, stripe_charge.refunded)

    stripe_subscription = processor.stripe_get_object(processor.stripe.Subscription, stripe_invoice.subscription)
    subscription = processor.get_subscription(stripe_subscription)

    if not subscription:
        msg = f"Stripe Subscription Invoice was not processed: stripe_invoice: {stripe_invoice}"
        logger.error(msg)
        return HttpResponse(status=200, content=msg)
    
    stripe_product = processor.stripe_get_object(processor.stripe.Product, stripe_subscription.plan.product)
    offer = processor.get_offer_from_stripe_product(stripe_product)

    customer_profile, stripe_customer = processor.get_customer_profile_and_stripe_customer(stripe_invoice.customer)

    if not offer or not customer_profile:
        msg = f"Stripe Subscription Invoice was not processed, stripe_invoice: {stripe_invoice.id} offer: {offer}, customer_profile: {customer_profile} stripe_customer: {stripe_customer}"
        logger.error(msg)
        return HttpResponse(status=200, content=msg)

    processor.invoice, created = processor.get_or_create_invoice_from_stripe_invoice(stripe_invoice, offer, customer_profile)
    processor.renew_subscription(subscription, stripe_invoice.charge, payment_status, payment_success=True, submitted_date=paid_date)

    # Remove any lingering payments. 
    for payment in processor.invoice.payments.filter(transaction__in=[None, '']):
        if (receipt := payment.get_receipt()):
            receipt.delete()
        payment.delete()

    return HttpResponse(status=200, content=f"Subscription: {stripe_subscription.id} renewed invoice: {processor.invoice.pk}")


class StripeInvoicePaymentSuccededEvent(StripeBaseAPI):
    def post(self, request, *args, **kwargs):
        site = get_site_from_request(self.request)

        if not self.is_valid_post(site):
            logger.error("StripeInvoicePaid error: invalid post")
            return HttpResponse(status=200, content="StripeInvoicePaid error: invalid post")

        if not self.is_incoming_event_correct(self.event, StripeEvents.INOVICE_PAYMENT_SUCCEEDED):
            logger.error(f"StripeInvoicePaid error: invalid event {self.event}")
            return HttpResponse(status=200, content=f"StripeInvoicePaid error: invalid event {self.event}")

        stripe_invoice = self.event.data.object
        
        if 'subscription' not in stripe_invoice or not stripe_invoice['subscription']:
            # Line Items Invoice
            return process_stripe_invoice_line_items_payment_succeded(stripe_invoice, site)
        else:
            # Subscription Invoice
            return process_stripe_invoice_subscription_payment_succeded(stripe_invoice, site)


class StripeInvoiceUpcomingEvent(StripeBaseAPI):
    def post(self, request, *args, **kwargs):
        site = get_site_from_request(request)
        processor = StripeProcessor(site)

        if not self.is_valid_post(site):
            logger.error("StripeInvoicePaid error: invalid post")
            return HttpResponse(status=200, content="StripeInvoicePaid error: invalid post")

        if not self.is_incoming_event_correct(self.event, StripeEvents.INVOICE_UPCOMING):
            logger.error(f"StripeInvoicePaid error: invalid event {self.event}")
            return HttpResponse(status=200, content=f"StripeInvoicePaid error: invalid event {self.event}")

        stripe_invoice = self.event.data.object
        customer_profile, stripe_customer = processor.get_customer_profile_and_stripe_customer(stripe_invoice.customer)
        if not customer_profile or not stripe_customer:
            logger.error(f"error retrieving customer information for request: {self.event}")
            return HttpResponse(status=200)
        
        logger.info(f"Upcoming Invoice for stripe_customer: {stripe_customer} customer_profile: {customer_profile}")

        stripe_invoice_upcoming.send(sender=self.__class__, customer_profile=customer_profile)
