from django.urls import path

from vendor.api.v1 import views as api_views

app_name = "vendor_api"

urlpatterns = [
    # Shared API Endpoints
    path(
        "cart/<slug:slug>/add/", api_views.AddToCartView.as_view(), name="add-to-cart"
    ),
    path(
        "cart/<slug:slug>/remove/",
        api_views.RemoveFromCartView.as_view(),
        name="remove-from-cart",
    ),
    path(
        "subscription/<uuid:uuid>/cancel/",
        api_views.PaymentGatewaySubscriptionCancelView.as_view(),
        name="customer-subscription-cancel",
    ),
]
