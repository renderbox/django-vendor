# Models

Django Vendor centers around Products, Offers, Invoices, Payments, and Receipts.
The relationships are intentionally minimal so you can plug in your own catalog
and presentation layer.

## Core concepts

### Product

`ProductModelBase` is the base class for your catalog items. Subclass it in your
own app and point `VENDOR_PRODUCT_MODEL` in the Django settings at it.

Key fields:

- `sku`, `uuid`, `name`, `slug`, `available`
- `description` and `meta` (JSON)
- `offers` (many-to-many)
- `receipts` (many-to-many)

#### examples

Define your product model:

```python
# myapp/models.py
from vendor.models import ProductModelBase

class Product(ProductModelBase):
    pass
```

Point vendor at it:

```python
# settings.py
VENDOR_PRODUCT_MODEL = "myapp.Product"
```

### Offer

`Offer` is the purchasable unit. It can bundle one or more products and supports
one-time or subscription terms.

Key fields:

- `products` (many-to-many)
- `terms`, `term_details` (JSON), `available`
- `start_date`, `end_date`
- `offer_description`, `allow_multiple`, `is_promotional`

Offers are what users add to cart; Products are what they ultimately receive.

### Invoice and OrderItem

`Invoice` represents a cart or an order. `OrderItem` ties an `Offer` to an
invoice with a quantity and pricing details.

Invoices progress from cart to checkout to complete based on payment processor
callbacks.

### Payment

`Payment` tracks gateway transactions for an invoice. It stores the processor
status, success flag, transaction id, and the gateway response payload.

### Receipt

`Receipt` represents access to purchased products. Receipts can be time-bound
(start/end dates) and are used to determine ownership and access.

### Subscription

`Subscription` tracks recurring purchases and the gateway subscription id. It
links to offers and receipts so access can be updated on renewals or cancels.

## Supporting models

- `CustomerProfile` ties users to a site and stores billing/shipping data.
- `Address` stores billing and shipping addresses.
- `Price` attaches pricing to offers (with priority and active date ranges).
- `TaxClassifier` and related models support tax configuration.

## References

For field-level detail, see the model docstrings and type hints in
`vendor.models`.

## Usage examples

Create a product and offer in the Django shell:

```python
from django.contrib.sites.models import Site
from django.utils import timezone

from vendor.models import Offer, Price
from myapp.models import Product
from vendor.models.choice import TermType

site = Site.objects.get_current()

product = Product.objects.create(
    name="Pro Plan",
    site=site,
    available=True,
    meta={"msrp": {"default": "usd", "usd": 49.00}},
)

offer = Offer.objects.create(
    site=site,
    name="Pro Plan Monthly",
    start_date=timezone.now(),
    terms=TermType.SUBSCRIPTION,
    available=True,
)
offer.products.add(product)

Price.objects.create(
    offer=offer,
    cost=49.00,
    currency="usd",
    priority=10,
)
```

Add an offer to a user's cart:

```python
from vendor.utils import get_site_from_request
from vendor.models import Offer

site = get_site_from_request(request)
offer = Offer.objects.get(site=site, slug="pro-plan-monthly")

profile, _ = request.user.customer_profile.get_or_create(site=site)
cart = profile.get_cart_or_checkout_cart()
cart.add_offer(offer)
```

Link to add/remove from cart in a template:

```django
<a href="{% url 'vendor_api:add-to-cart' offer.slug %}">Add to cart</a>
<a href="{% url 'vendor_api:remove-from-cart' offer.slug %}">Remove</a>
```
