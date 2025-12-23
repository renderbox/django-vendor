import json
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import RequestFactory

stripe = pytest.importorskip("stripe")

from vendor.api.v1.stripe.views.elements import (  # noqa: E402
    StripeCreatePaymentIntent,
    StripeEvents,
    StripeWebhookEventHandler,
)
from vendor.models import CustomerProfile, Offer, Subscription  # noqa: E402
from vendor.models.choice import SubscriptionStatus, TermType  # noqa: E402
from vendor.processors import StripeProcessor  # noqa: E402


@pytest.fixture
def db_with_fixtures(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "user", "unit_test")


@pytest.mark.django_db
def test_stripe_create_payment_intent_requires_payment_method(db_with_fixtures):
    request_factory = RequestFactory()
    site = Site.objects.get_current()
    user = get_user_model().objects.get(pk=1)

    request = request_factory.post("/stripe/payment-intent/", data={})
    request.user = user
    request.site = site

    response = StripeCreatePaymentIntent.as_view()(request)

    assert response.status_code == 400
    payload = json.loads(response.content)
    assert payload["error"] == "payment_method_id is required"


@pytest.mark.django_db
def test_stripe_create_payment_intent_success(db_with_fixtures, monkeypatch):
    request_factory = RequestFactory()
    site = Site.objects.get_current()
    user = get_user_model().objects.get(pk=1)
    profile = CustomerProfile.objects.get(user=user, site=site)
    profile.meta["stripe_id"] = "cus_test"
    profile.save()

    offer = Offer.objects.filter(
        terms__gte=TermType.PERPETUAL, prices__cost__gt=0
    ).first()
    invoice = profile.get_cart_or_checkout_cart()
    invoice.empty_cart()
    invoice.add_offer(offer)

    def noop_processor_setup(self, site, source=None):
        self.site = site

    captured_intent_data = {}

    def stub_create_payment_intent(self, payment_intent_data):
        captured_intent_data.update(payment_intent_data)
        return SimpleNamespace(
            id="pi_test",
            client_secret="secret_test",
            amount=payment_intent_data["amount"],
            currency=payment_intent_data["currency"],
        )

    monkeypatch.setattr(StripeProcessor, "processor_setup", noop_processor_setup)
    monkeypatch.setattr(StripeProcessor, "validate_invoice_customer_in_stripe", lambda self: None)
    monkeypatch.setattr(StripeProcessor, "validate_invoice_offer_in_stripe", lambda self: None)
    monkeypatch.setattr(StripeProcessor, "create_payment_intent", stub_create_payment_intent)

    request = request_factory.post(
        "/stripe/payment-intent/",
        data={"payment_method_id": "pm_test"},
    )
    request.user = user
    request.site = site

    response = StripeCreatePaymentIntent.as_view()(request)

    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload["payment_intent_id"] == "pi_test"
    assert payload["client_secret"] == "secret_test"
    assert payload["amount"] == captured_intent_data["amount"]
    assert payload["currency"] == captured_intent_data["currency"]


@pytest.mark.django_db
def test_stripe_webhook_subscription_deleted_updates_status(
    db_with_fixtures, monkeypatch
):
    request_factory = RequestFactory()
    site = Site.objects.get_current()
    user = get_user_model().objects.get(pk=1)
    profile = CustomerProfile.objects.get(user=user, site=site)

    subscription = Subscription.objects.create(
        profile=profile,
        gateway_id="sub_test",
        status=SubscriptionStatus.ACTIVE,
    )

    event = SimpleNamespace(
        type=StripeEvents.SUBSCRIPTION_DELETED,
        data=SimpleNamespace(object=SimpleNamespace(id="sub_test")),
    )

    def stub_is_valid_post(self, site):
        self.event = event
        return True

    def noop_processor_setup(self, site, source=None):
        self.site = site

    monkeypatch.setattr(StripeWebhookEventHandler, "is_valid_post", stub_is_valid_post)
    monkeypatch.setattr(StripeProcessor, "processor_setup", noop_processor_setup)

    request = request_factory.post("/stripe/webhook/")
    request.site = site

    response = StripeWebhookEventHandler.as_view()(request)

    assert response.status_code == 200
    subscription.refresh_from_db()
    assert subscription.status == SubscriptionStatus.CANCELED
