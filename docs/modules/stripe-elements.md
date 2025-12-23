# Stripe Elements API

This module provides a small Stripe API surface used by the frontend checkout
flow and Stripe webhooks.

Files:

- `vendor.api.stripe.elements.views`
- `vendor.api.stripe.elements.urls`

## URL wiring

Include the Stripe Elements routes under your API prefix:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("sales/api/stripe/", include("vendor.api.stripe.elements.urls")),
]
```

## Endpoints

### Create PaymentIntent

`POST /sales/api/stripe/payment-intent/`

Creates a Stripe PaymentIntent for the current cart (one-time items only).

Request body (form or JSON):

- `payment_method_id` (required): Stripe PaymentMethod id (e.g., `pm_123`)
- `invoice_uuid` (optional): target a specific invoice; defaults to cart/checkout

Response (JSON):

```json
{
  "payment_intent_id": "pi_123",
  "client_secret": "pi_123_secret_456",
  "amount": 5000,
  "currency": "usd"
}
```

Notes:

- Requires authentication.
- The customer profile must have `meta["stripe_id"]`.
- Only one-time charges are included (subscriptions are excluded).

### Stripe Webhook

`POST /sales/api/stripe/webhook/`

Single webhook entry point for Stripe events. It validates the event signature,
routes by event type, and updates Vendor models as needed.

Handled events include:

- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `invoice.upcoming`
- `invoice.finalized`
- `invoice.payment_action_required`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`
- `charge.succeeded`
- `charge.refunded`
- `charge.refund.updated`
- `customer.updated`
- `customer.source.expired`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `customer.subscription.trial_will_end`
- `setup_intent.succeeded`
- `charge.dispute.created`
- `charge.dispute.closed`

Configure Stripe to send webhooks to the URL above. The handler returns HTTP 200
for valid and unhandled events.

## Example requests

Create PaymentIntent:

```bash
curl -X POST http://localhost:8000/sales/api/stripe/payment-intent/ \
  -d payment_method_id=pm_test
```
