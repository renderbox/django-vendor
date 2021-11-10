from django.urls import path

from vendor.api.v1 import views as api_views
from vendor.api.v1.authorizenet import views as authorizenet_views

app_name = "vendor_api"

urlpatterns = [
    path('', api_views.VendorIndexAPI.as_view(), name='api-index'),
    path('cart/add/<slug:slug>/', api_views.AddToCartView.as_view(), name="add-to-cart"),
    path('cart/remove/<slug:slug>/', api_views.RemoveFromCartView.as_view(), name="remove-from-cart"),
    path('customer/subscription/<uuid:uuid>/cancel/', api_views.SubscriptionCancelView.as_view(), name="customer-subscription-cancel"),
    path('product/<uuid:uuid>/remove', api_views.VoidProductView.as_view(), name="manager-profile-remove-product"),
    path('profile/<uuid:uuid_profile>/offer/<uuid:uuid_offer>/add', api_views.AddOfferToProfileView.as_view(), name="manager-profile-add-offer"),
    path('product/<uuid:uuid>/availability', api_views.ProductAvailabilityToggleView.as_view(), name="manager-product-availablility"),
    path('subscription/price/update', api_views.SubscriptionPriceUpdateView.as_view(), name="manager-subscription-price-update"),
    path('authorizenet/authcapture', authorizenet_views.AuthorizeCaptureAPI.as_view(), name='api-authorizenet-authcapture-get')
]