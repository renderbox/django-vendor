# Payment Processors

Vendor provides a processor interface and a Stripe implementation. Processors
are responsible for turning invoices into charges, managing subscription
lifecycle, and creating receipts.

Files:

- `vendor.processors.base`
- `vendor.processors.stripe`

## Architecture

`PaymentProcessorBase` defines the shared workflow:

- accept a site + invoice
- perform pre-authorization checks
- run the gateway transaction
- record payments and update invoice status
- create receipts and subscriptions as needed

Processor hooks you typically override:

- `processor_setup(site)` for credentials and SDK setup
- `set_api_endpoint()` for environment-specific endpoints
- gateway-specific charge/authorize/refund methods

## StripeProcessor

`StripeProcessor` handles:

- syncing CustomerProfiles, Offers, and Prices to Stripe
- creating PaymentIntents for one-time charges
- creating and updating Stripe subscriptions
- handling webhook-driven renewals and failures

Stripe uses site-specific credentials stored via `StripeIntegration` or
settings (`STRIPE_SECRET_KEY`).

## Usage

Select the processor by site config:

```python
# settings.py (global default)
VENDOR_PAYMENT_PROCESSOR = "stripe.StripeProcessor"
```

Or via site config in the admin (recommended for multi-site setups).

Use in code:

```python
from vendor.processors import StripeProcessor

processor = StripeProcessor(site, invoice)
processor.pre_authorization()
processor.process_payment()
processor.post_authorization()
```

## Notes

- Stripe requires webhooks for subscription renewals and payment updates.
- For testing, mock Stripe calls or use `stripe-mock` for integration tests.
