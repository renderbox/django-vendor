from django.urls import path

from vendor.api.v1.stripe.views.elements import (
    StripeCreatePaymentIntent,
    StripeWebhookEventHandler,
)

app_name = "vendor_api"

urlpatterns = [
    # Stripe Specific API Endpoints
    # Payment Intents
    path(
        "payment-intent/",
        StripeCreatePaymentIntent.as_view(),
        name="stripe-payment-intent-create",
    ),
    # Webhook
    path(
        "webhook/",
        StripeWebhookEventHandler.as_view(),
        name="stripe-webhook",
    ),
]
