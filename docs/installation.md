# Installation

## Requirements

- Python 3.10+
- Django 5.2+
- `django-site-configs` (site-scoped configuration)
- `django-integrations` (stores payment processor credentials)
- Django sites framework enabled (`django.contrib.sites`)

## Install the package

```bash
pip install django-vendor
```

Optional payment processors:

```bash
pip install "django-vendor[stripe]"
pip install "django-vendor[authorizenet]"
```

If you do not already have them, install the required companion apps:

```bash
pip install django-site-configs django-integrations
```

## Configure Django

Add the apps to `INSTALLED_APPS` and enable sites:

```python
INSTALLED_APPS = [
    # ...
    "django.contrib.sites",
    "siteconfigs",
    "integrations",
    "vendor",
]

SITE_ID = 1
```

Define a product model. You do this by subclassing ProductModelBase to make sure that some required features are added to the model.

```python
# myapp/models.py
from vendor.models import ProductModelBase


class MyProduct(ProductModelBase):
    pass
```

Then point vendor at it:

```python
VENDOR_PRODUCT_MODEL = "myapp.MyProduct"
```

Common settings (defaults shown):

```python
VENDOR_PAYMENT_PROCESSOR = "dummy.DummyProcessor"
VENDOR_STATE = "DEBUG"  # Use "PRODUCTION" in production
VENDOR_DATA_ENCODER = "vendor.encrypt.cleartext"
DEFAULT_CURRENCY = "usd"
```

If you want to constrain available billing countries:

```python
VENDOR_COUNTRY_CHOICE = ["US", "CA"]
VENDOR_COUNTRY_DEFAULT = "US"
```

## URLs

Wire up the user, admin, and API endpoints (examples shown):

```python
from django.urls import include, path

urlpatterns = [
    # ...
    # Rendered Template Views
    path("sales/", include("vendor.urls.vendor")), 
    path("sales/manage/", include("vendor.urls.vendor_admin")),
    # API Views
    path("api/sales/", include("vendor.api.v1.urls")),
]
```

## Migrate

After your project is all setup, run the Django migrations.

```bash
python manage.py migrate
```

## Usage

1. Create product items in the admin.
2. Create offers with prices for those products.
3. Link users to the cart/checkout flow or use the API endpoints.

Useful entry points:

- `vendor:cart` and the checkout views under `vendor:checkout-*`
- `vendor_api:add-to-cart` / `vendor_api:remove-from-cart`
- `vendor_admin:manager-dashboard` for admin management

Example add-to-cart link in a template:

```django
<a href="{% url 'vendor_api:add-to-cart' offer.slug %}">Add to cart</a>
```
