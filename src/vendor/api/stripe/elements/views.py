import json
import logging

import stripe
from django import dispatch
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import TextChoices
from django.http import JsonResponse
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from vendor.integrations import StripeIntegration
from vendor.models import CustomerProfile, Invoice, Subscription
from vendor.models.choice import InvoiceStatus, PurchaseStatus
from vendor.processors import StripeProcessor
from vendor.utils import get_site_from_request

logger = logging.getLogger(__name__)


##########
# SIGNALS
stripe_invoice_upcoming = dispatch.Signal()


class StripeEvents(TextChoices):
    INVOICE_PAID = "invoice.paid", _("Invoice Paid")
    INVOICE_PAYMENT_FAILED = "invoice.payment_failed", _("Invoice Payment Failed")
    INOVICE_PAYMENT_SUCCEEDED = "invoice.payment_succeeded", _(
        "Invoice Payment Succeeded"
    )
    INVOICE_UPCOMING = "invoice.upcoming", _("Upcoming Invoice")
    PAYMENT_INTENT_SUCCEDED = "payment_intent.succeeded", _("Payment Succeeded")
    PAYMENT_INTENT_PAYMENT_FAILED = "payment_intent.payment_failed", _(
        "Payment Intent Failed"
    )
    CHARGE_SUCCEEDED = "charge.succeeded", _("Charge Succeeded")
    CHARGE_REFUNDED = "charge.refunded", _("Charge Refunded")
    CHARGE_REFUND_UPDATED = "charge.refund.updated", _("Charge Refund Updated")
    SOURCE_EXPIRED = "customer.source.expired", _("Source Expired")
    CUSTOMER_UPDATED = "customer.updated", _("Customer Updated")
    SUBSCRIPTION_UPDATED = "customer.subscription.updated", _("Subscription Updated")
    SUBSCRIPTION_CREATED = "customer.subscription.created", _("Subscription Created")
    SUBSCRIPTION_DELETED = "customer.subscription.deleted", _("Subscription Deleted")
    SUBSCRIPTION_TRIAL_END = "customer.subscription.trial_will_end", _(
        "Trial Period Will End"
    )
    INVOICE_FINALIZED = "invoice.finalized", _("Invoice Finalized")
    INVOICE_PAYMENT_ACTION_REQUIRED = "invoice.payment_action_required", _(
        "Invoice Payment Action Required"
    )
    SETUP_INTENT_SUCCEEDED = "setup_intent.succeeded", _("Setup Intent Succeeded")
    CHARGE_DISPUTE_CREATED = "charge.dispute.created", _("Charge Dispute Created")
    CHARGE_DISPUTE_CLOSED = "charge.dispute.closed", _("Charge Dispute Closed")


class StripeBaseAPI(View):
    """Base webhook view that validates Stripe signatures and parses events."""

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
                self.event = stripe.Event.construct_from(
                    json.loads(self.request.body), credentials.instance.private_key
                )
            elif settings.STRIPE_PUBLIC_KEY:
                self.event = stripe.Event.construct_from(
                    json.loads(self.request.body), settings.STRIPE_PUBLIC_KEY
                )
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
        if self.event.data.object.billing_reason != "subscription_cycle":
            return False

        return True

    def is_incoming_event_correct(self, event, desired_event):
        if event.type != desired_event:
            return False

        return True


# ### Stripe Elements Endpoints ###


class StripeWebhookEventHandler(StripeBaseAPI):
    """
    A single Stripe webhook handler that routes events to specific handlers.

    NOTE: Many of the handlers are stubs that log the event for future extension.
    The key implemented handlers reconcile invoice payments for one-time purchases
    and subscription renewals, as well as handling failed subscription payments.
    """

    def post(self, request, *args, **kwargs):
        self.site = get_site_from_request(self.request)
        self.processor = StripeProcessor(self.site)

        if not self.is_valid_post(self.site):
            logger.error("StripeWebhookEventHandler error: invalid post")
            return HttpResponse(
                status=200, content="StripeWebhookEventHandler error: invalid post"
            )

        event_type = self.event.type
        handler = self.get_event_handler(event_type)
        if not handler:
            logger.info(f"StripeWebhookEventHandler: unhandled event {event_type}")
            return HttpResponse(status=200)

        return handler()

    def get_event_handler(self, event_type):
        handlers = {
            StripeEvents.INOVICE_PAYMENT_SUCCEEDED: self.event_invoice_payment_succeeded,
            StripeEvents.INVOICE_UPCOMING: self.event_invoice_upcoming,
            StripeEvents.INVOICE_PAYMENT_FAILED: self.event_invoice_payment_failed,
            StripeEvents.INVOICE_FINALIZED: self.event_invoice_finalized,
            StripeEvents.INVOICE_PAYMENT_ACTION_REQUIRED: self.event_invoice_payment_action_required,
            StripeEvents.SOURCE_EXPIRED: self.event_source_expired,
            StripeEvents.PAYMENT_INTENT_SUCCEDED: self.event_payment_intent_succeeded,
            StripeEvents.PAYMENT_INTENT_PAYMENT_FAILED: self.event_payment_intent_failed,
            StripeEvents.CHARGE_SUCCEEDED: self.event_charge_succeeded,
            StripeEvents.CHARGE_REFUNDED: self.event_charge_refunded,
            StripeEvents.CHARGE_REFUND_UPDATED: self.event_charge_refund_updated,
            StripeEvents.CUSTOMER_UPDATED: self.event_customer_updated,
            StripeEvents.SUBSCRIPTION_UPDATED: self.event_subscription_updated,
            StripeEvents.SUBSCRIPTION_CREATED: self.event_subscription_created,
            StripeEvents.SUBSCRIPTION_DELETED: self.event_subscription_deleted,
            StripeEvents.SUBSCRIPTION_TRIAL_END: self.event_subscription_trial_will_end,
            StripeEvents.SETUP_INTENT_SUCCEEDED: self.event_setup_intent_succeeded,
            StripeEvents.CHARGE_DISPUTE_CREATED: self.event_charge_dispute_created,
            StripeEvents.CHARGE_DISPUTE_CLOSED: self.event_charge_dispute_closed,
        }

        return handlers.get(event_type, self.event_unhandled)

    def event_unhandled(self):
        event_type = getattr(self.event, "type", None)
        event_id = getattr(self.event, "id", None)
        logger.info(
            "StripeWebhookEventHandler: unhandled event %s id=%s",
            event_type,
            event_id,
        )
        return HttpResponse(status=200)

    def event_invoice_payment_succeeded(self):
        """
        Reconcile successful invoice payments into local records.

        Stripe sends this when an invoice is paid. We either create receipts for
        one-time purchases or renew subscriptions tied to the invoice.
        """
        stripe_invoice = self.event.data.object

        # Single Payment for One-Time Purchase (No Subscription) Success
        if "subscription" not in stripe_invoice or not stripe_invoice["subscription"]:
            return self._process_stripe_invoice_line_items_payment_succeded(
                stripe_invoice
            )

        # Subscription Payment Success
        return self._process_stripe_invoice_subscription_payment_succeded(
            stripe_invoice
        )

    def _process_stripe_invoice_line_items_payment_succeded(self, stripe_invoice):

        customer_profile, stripe_customer = (
            self.processor.get_customer_profile_and_stripe_customer(
                stripe_invoice.customer
            )
        )

        stripe_charge = self.processor.stripe_get_object(
            self.processor.stripe.Charge, stripe_invoice.charge
        )
        stripe_payment_method = self.processor.stripe_get_object(
            self.processor.stripe.PaymentMethod, stripe_charge.payment_method
        )

        offers = self.processor.get_offers_from_invoice_line_items(
            stripe_invoice.lines["data"]
        )

        for offer in offers:
            self.processor.invoice, created = (
                self.processor.get_or_create_invoice_from_stripe_invoice(
                    stripe_invoice, offer, customer_profile
                )
            )

        payment = self.processor.get_or_create_payment_from_stripe_payment_and_charge(
            self.processor.invoice, stripe_payment_method, stripe_charge
        )

        if payment.status == PurchaseStatus.SETTLED:
            self.processor.create_single_purchase_receipts(
                self.processor.invoice, payment, stripe_charge
            )

    def _process_stripe_invoice_subscription_payment_succeded(self, stripe_invoice):
        paid_date = timezone.datetime.fromtimestamp(
            stripe_invoice.status_transitions.paid_at, tz=timezone.utc
        )
        payment_status = PurchaseStatus.SETTLED

        if stripe_invoice.charge:
            stripe_charge = self.processor.stripe_get_object(
                self.processor.stripe.Charge, stripe_invoice.charge
            )
            payment_status = self.processor.get_payment_status(
                stripe_charge.status, stripe_charge.refunded
            )

        stripe_subscription = self.processor.stripe_get_object(
            self.processor.stripe.Subscription, stripe_invoice.subscription
        )
        subscription = self.processor.get_subscription(stripe_subscription)

        if not subscription:
            msg = f"Stripe Subscription Invoice was not processed: stripe_invoice: {stripe_invoice}"
            logger.error(msg)
            return HttpResponse(status=200, content=msg)

        stripe_product = self.processor.stripe_get_object(
            self.processor.stripe.Product, stripe_subscription.plan.product
        )
        offer = self.processor.get_offer_from_stripe_product(stripe_product)

        customer_profile, stripe_customer = (
            self.processor.get_customer_profile_and_stripe_customer(
                stripe_invoice.customer
            )
        )

        if not offer or not customer_profile:
            msg = f"Stripe Subscription Invoice was not processed, stripe_invoice: {stripe_invoice.id} offer: {offer}, customer_profile: {customer_profile} stripe_customer: {stripe_customer}"  # noqa: E501
            logger.error(msg)
            return HttpResponse(status=200, content=msg)

        self.processor.invoice, created = (
            self.processor.get_or_create_invoice_from_stripe_invoice(
                stripe_invoice, offer, customer_profile
            )
        )
        self.processor.renew_subscription(
            subscription,
            stripe_invoice.charge,
            payment_status,
            payment_success=True,
            submitted_date=paid_date,
        )

        # Remove any lingering payments.
        for payment in self.processor.invoice.payments.filter(
            transaction__in=[None, ""]
        ):
            if receipt := payment.get_receipt():
                receipt.delete()
            payment.delete()

        return HttpResponse(
            status=200,
            content=f"Subscription: {stripe_subscription.id} renewed invoice: {self.processor.invoice.pk}",
        )

    def event_invoice_upcoming(self):
        """
        Respond to Stripe's heads-up that a charge is about to happen.

        Stripe sends invoice.upcoming shortly before attempting to bill a
        subscription. We use it to resolve the customer profile and emit the
        `stripe_invoice_upcoming` signal so downstream code can notify the user
        or run pre-billing checks.
        """
        stripe_invoice = self.event.data.object

        customer_profile, stripe_customer = (
            self.processor.get_customer_profile_and_stripe_customer(
                stripe_invoice.customer
            )
        )
        if not customer_profile or not stripe_customer:
            logger.error(
                f"error retrieving customer information for request: {self.event}"
            )
            return HttpResponse(status=200)

        logger.info(
            f"Upcoming Invoice for stripe_customer: {stripe_customer} customer_profile: {customer_profile}"
        )

        stripe_invoice_upcoming.send(
            sender=self.__class__, customer_profile=customer_profile
        )
        return HttpResponse(status=200)

    def event_invoice_payment_failed(self):
        """
        Handle a failed subscription billing attempts from Stripe.

        Stripe sends invoice.payment_failed when a recurring charge cannot be
        collected. We create a local invoice tied to the offer so support or
        automated flows can detect the failure and follow up with the customer.
        """
        stripe_invoice = self.event.data.object
        paid_date = timezone.datetime.fromtimestamp(
            stripe_invoice.effective_at, tz=timezone.utc
        )

        customer_profile, stripe_customer = (
            self.processor.get_customer_profile_and_stripe_customer(
                stripe_invoice.customer
            )
        )
        if not customer_profile:
            logger.error(
                f"StripeWebhookEventHandler error: email: {stripe_invoice.customer_email} does not exist"
            )
            return HttpResponse(status=200)

        try:
            subscription = Subscription.objects.get(
                gateway_id=stripe_invoice.subscription, profile=customer_profile
            )
        except ObjectDoesNotExist:
            logger.error(
                f"StripeWebhookEventHandler customer: {customer_profile} does not have a subscription with stripe_id: {stripe_invoice.subscription}"  # noqa: E501
            )
            return HttpResponse(status=200)

        offer = subscription.get_offer()

        if not offer:
            logger.error(
                f"StripeWebhookEventHandler {subscription} has no offer attached"
            )
            return HttpResponse(status=200)

        invoice = Invoice.objects.create(
            profile=subscription.profile,
            site=subscription.profile.site,
            ordered_date=paid_date,
            status=InvoiceStatus.COMPLETE,
        )

        invoice.add_offer(offer)
        invoice.vendor_notes = {}
        invoice.vendor_notes["stripe_id"] = stripe_invoice.stripe_id
        invoice.save()
        self.processor.invoice = invoice
        self.processor.subscription_payment_failed(subscription, stripe_invoice.charge)

        return HttpResponse(status=200)

    def event_source_expired(self):
        """
        Handle expiring customer payment sources.

        Stripe emits customer.source.expired when a saved card is expiring or
        removed. We use it to find the local customer and trigger the processor
        hook that can notify them to update payment details.
        """
        stripe_card = self.event.data.object
        stripe_customer_id = stripe_card["customer"]
        if not stripe_customer_id:
            return HttpResponse(status=200)

        try:
            customer_profile = CustomerProfile.objects.get(
                meta__stripe_id=stripe_customer_id
            )
        except ObjectDoesNotExist:
            logger.error(
                f"StripeWebhookEventHandler: stripe id {stripe_customer_id} does not exist for customer in vendor"
            )
            return HttpResponse(status=200)

        email = customer_profile.user.email
        logger.info(
            f"StripeWebhookEventHandler: sending customer_source_expiring signal for site {self.site} and email {email}"  # noqa: E501
        )

        self.processor.customer_card_expired(self.site, email)

        return HttpResponse(status=200)

    def event_payment_intent_succeeded(self):
        """
        Acknowledge a completed PaymentIntent for one-off payments.

        This confirms Stripe captured funds successfully. We currently log the
        outcome and can extend it to reconcile local payments.
        """
        logger.info(
            f"StripeWebhookEventHandler: payment_intent.succeeded {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_payment_intent_failed(self):
        """
        Capture failed PaymentIntent attempts for follow-up.

        Indicates the payment method failed. We log it and can later trigger a
        retry or customer notification flow.
        """
        logger.info(
            f"StripeWebhookEventHandler: payment_intent.payment_failed {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_charge_succeeded(self):
        """
        Record successful charges outside invoice-driven flows.

        Useful for legacy or custom charge paths; we log and can reconcile later.
        """
        logger.info(
            f"StripeWebhookEventHandler: charge.succeeded {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_charge_refunded(self):
        """
        Observe refunds to keep local records aligned.

        Stripe emits this on full or partial refunds. We log and can later
        update payment and access records.
        """
        logger.info(
            f"StripeWebhookEventHandler: charge.refunded {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_charge_refund_updated(self):
        """
        Track updates to an existing refund.

        Used for refund status changes (partial or failed) and future syncing.
        """
        refund = self.event.data.object
        logger.info(f"StripeWebhookEventHandler: charge.refund.updated {refund.id}")
        return HttpResponse(status=200)

    def event_customer_updated(self):
        """
        Observe customer record changes from Stripe.

        This lets us sync email or metadata changes if needed. Currently we
        log for visibility and can extend to persist updates.
        """
        logger.info(
            f"StripeWebhookEventHandler: customer.updated {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_subscription_created(self):
        """
        Create or sync a subscription when Stripe provisions it.

        Stripe emits this when a subscription is first created. We ensure a
        matching local Subscription exists so renewals and access tracking work.
        """
        stripe_subscription = self.event.data.object

        customer_profile, _stripe_customer = (
            self.processor.get_customer_profile_and_stripe_customer(
                stripe_subscription.customer
            )
        )
        if not customer_profile:
            logger.error(
                f"StripeWebhookEventHandler: customer not found for subscription {stripe_subscription.id}"
            )
            return HttpResponse(status=200)

        self.processor.get_or_create_subscription_from_stripe_subscription(
            customer_profile, stripe_subscription
        )
        return HttpResponse(status=200)

    def event_subscription_updated(self):
        """
        Sync subscription status changes from Stripe.

        This covers state transitions like trialing, past_due, or paused so the
        local subscription remains accurate for access control.
        """
        stripe_subscription = self.event.data.object

        customer_profile, _stripe_customer = (
            self.processor.get_customer_profile_and_stripe_customer(
                stripe_subscription.customer
            )
        )
        if not customer_profile:
            logger.error(
                f"StripeWebhookEventHandler: customer not found for subscription {stripe_subscription.id}"
            )
            return HttpResponse(status=200)

        subscription, _created = (
            self.processor.get_or_create_subscription_from_stripe_subscription(
                customer_profile, stripe_subscription
            )
        )
        if subscription:
            subscription.status = self.processor.get_subscription_status(
                stripe_subscription.status
            )
            subscription.save()

        return HttpResponse(status=200)

    def event_subscription_deleted(self):
        """
        Mark local subscriptions as canceled when Stripe removes them.

        Keeps local status aligned with Stripe-initiated cancellations.
        """
        stripe_subscription = self.event.data.object

        subscription = self.processor.get_subscription(stripe_subscription)
        if not subscription:
            logger.error(
                f"StripeWebhookEventHandler: subscription not found {stripe_subscription.id}"
            )
            return HttpResponse(status=200)

        subscription.status = self.processor.get_subscription_status("canceled")
        subscription.save()

        return HttpResponse(status=200)

    def event_invoice_finalized(self):
        """
        Note when Stripe finalizes an invoice.

        This indicates invoice totals are locked; useful for audits or alerts.
        """
        logger.info(
            f"StripeWebhookEventHandler: invoice.finalized {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_invoice_payment_action_required(self):
        """
        Note when Stripe requires customer action to complete payment.

        Typically indicates SCA/3DS is needed; useful for prompting the user.
        """
        logger.info(
            f"StripeWebhookEventHandler: invoice.payment_action_required {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_subscription_trial_will_end(self):
        """
        Warn that a subscription trial is nearing completion.

        Used to trigger reminders or upgrade prompts before billing begins.
        """
        stripe_subscription = self.event.data.object
        logger.info(
            f"StripeWebhookEventHandler: trial will end for subscription {stripe_subscription.id}"
        )
        return HttpResponse(status=200)

    def event_setup_intent_succeeded(self):
        """
        Confirm a payment method was saved for future use.

        Stripe emits this after a successful SetupIntent; useful for onboarding
        or enabling subscription starts.
        """
        logger.info(
            f"StripeWebhookEventHandler: setup_intent.succeeded {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_charge_dispute_created(self):
        """
        Record that a chargeback/dispute was opened.

        Useful for alerting staff or restricting access pending resolution.
        """
        logger.info(
            f"StripeWebhookEventHandler: charge.dispute.created {self.event.data.object.id}"
        )
        return HttpResponse(status=200)

    def event_charge_dispute_closed(self):
        """
        Record dispute resolution.

        Used to clear alerts or restore access once resolved.
        """
        logger.info(
            f"StripeWebhookEventHandler: charge.dispute.closed {self.event.data.object.id}"
        )
        return HttpResponse(status=200)


class StripeCreatePaymentIntent(LoginRequiredMixin, View):
    """Create a Stripe PaymentIntent for the current invoice's one-time charges."""

    def post(self, request, *args, **kwargs):
        site = get_site_from_request(request)
        data = self._get_request_data(request)

        payment_method_id = data.get("payment_method_id")
        if not payment_method_id:
            return JsonResponse({"error": "payment_method_id is required"}, status=400)

        invoice = self._get_invoice(request, site, data.get("invoice_uuid"))
        if not invoice.order_items.exists():
            return JsonResponse({"error": "Invoice has no order items"}, status=400)

        amount = invoice.get_one_time_transaction_total()
        if amount <= 0:
            return JsonResponse(
                {"error": "Invoice has no one-time charges"}, status=400
            )

        processor = StripeProcessor(site, invoice)
        processor.validate_invoice_customer_in_stripe()
        processor.validate_invoice_offer_in_stripe()

        payment_intent_data = processor.build_payment_intent(
            amount, payment_method_id, currency=invoice.currency
        )
        payment_intent = processor.create_payment_intent(payment_intent_data)

        if not payment_intent:
            return JsonResponse(
                {"error": "Unable to create payment intent"}, status=400
            )

        return JsonResponse(
            {
                "payment_intent_id": payment_intent.id,
                "client_secret": payment_intent.client_secret,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
            }
        )

    def _get_request_data(self, request):
        if request.body and "application/json" in request.content_type:
            try:
                return json.loads(request.body)
            except json.JSONDecodeError:
                return {}
        return request.POST

    def _get_invoice(self, request, site, invoice_uuid):
        if invoice_uuid:
            return get_object_or_404(
                Invoice,
                uuid=invoice_uuid,
                profile__user=request.user,
                profile__site=site,
            )

        profile, _ = request.user.customer_profile.get_or_create(site=site)
        return profile.get_cart_or_checkout_cart()
