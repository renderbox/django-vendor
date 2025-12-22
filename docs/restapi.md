# REST API

Vendor ships a small REST-ish API surface used by the cart flow, admin actions,
and payment processor webhooks. Most endpoints are HTML redirects rather than
pure JSON. Mount the API URLs wherever you included `vendor.api.v1.urls`.

Example base path used in these docs: `/sales/api/`

## Authentication and session behavior

- Anonymous users can add/remove items and are stored in session cart data.
- Most management actions require authentication (`LoginRequiredMixin`).
- Webhook endpoints are CSRF-exempt and expect signed provider payloads.

## Core endpoints

Cart and checkout helpers (redirect to cart):

| Method | Path | Name | Notes |
| --- | --- | --- | --- |
| GET, POST | `cart/add/<slug>/` | `vendor_api:add-to-cart` | Adds an offer by slug. Anonymous users use session cart. |
| POST | `cart/remove/<slug>/` | `vendor_api:remove-from-cart` | Removes an offer by slug. |

Subscriptions and admin actions:

| Method | Path | Name | Notes |
| --- | --- | --- | --- |
| POST | `customer/subscription/<uuid>/cancel/` | `vendor_api:customer-subscription-cancel` | Cancels a single subscription via the payment processor. |
| POST | `customer/subscription/cancel/model/` | `vendor_api:manager-customer-subscriptions-cancel-model` | Cancels all active subscriptions for the current user. |
| POST | `product/<uuid>/remove` | `vendor_api:manager-profile-remove-product` | Voids a product on a receipt. |
| GET | `profile/<uuid_profile>/offer/<uuid_offer>/add` | `vendor_api:manager-profile-add-offer` | Grants a zero-value offer to a profile. |
| POST | `product/<uuid>/availability` | `vendor_api:manager-product-availablility` | Toggles product/offer availability. |
| POST | `subscription/price/update` | `vendor_api:manager-subscription-price-update` | Updates a subscription price (expects `subscription_uuid`, `offer_uuid`). |

Refunds (JSON):

| Method | Path | Name | Notes |
| --- | --- | --- | --- |
| GET | `refund-payment/<uuid>/` | `vendor_api:refund-payment-api` | Returns refund form data as JSON. |
| POST | `refund-payment/<uuid>/` | `vendor_api:refund-payment-api` | Issues a refund and returns JSON result. |

## Payment processor webhooks

Authorize.Net (expects `X-Anet-Signature` HMAC header):

| Method | Path | Name | Notes |
| --- | --- | --- | --- |
| POST | `authorizenet/authcapture` | `vendor_api:api-authorizenet-authcapture` | Capture/settlement webhook. |
| POST | `authorizenet/void` | `vendor_api:api-authorizenet-void` | Void webhook. |
| GET | `authorizenet/sync/subscriptions/` | `vendor_api:api-authorizenet-sync-subscriptions` | Manual sync endpoint. |
| POST | `authorizenet/settled/transactions/` | `vendor_api:api-authorizenet-settled-transactions` | Updates payments to settled in a date range. |

Stripe (expects Stripe event payloads; uses configured Stripe credentials):

| Method | Path | Name | Notes |
| --- | --- | --- | --- |
| POST | `stripe/invoice/paid/` | `vendor_api:api-stripe-invoice-paid` | Legacy invoice paid handler. |
| POST | `stripe/invoice/payment/succeded/` | `vendor_api:api-stripe-invoice-payment-succeded` | Invoice payment succeeded handler (preferred). |
| POST | `stripe/subscription/invoice/paid/` | `vendor_api:api-stripe-subscription-invoice-paid` | Legacy subscription invoice paid handler. |
| POST | `stripe/subscription/invoice/payment/failed/` | `vendor_api:api-stripe-subscription-invoice-payment-failed` | Subscription payment failure handler. |
| POST | `stripe/card/expiring/` | `vendor_api:api-stripe-card-expiring` | Card expiring handler. |
| POST | `stripe/invoice/upcoming/` | `vendor_api:api-stripe-invoice-upcoming` | Upcoming invoice handler. |
| GET | `stripe/sync/objects/` | `vendor_api:api-stripe-sync-objects` | Manual sync endpoint. |

## Example

```bash
curl -X POST http://localhost:8000/sales/api/cart/add/my-offer-slug/
```
