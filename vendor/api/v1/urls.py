from django.urls import path

from vendor.api.v1 import views as api_views
from vendor.api.v1.authorizenet import views as authorizenet_views

app_name = "vendor_api"

urlpatterns = [
    path('', api_views.VendorIndexAPI.as_view(), name='api-index'),
    path('cart/add/<slug:slug>/', api_views.AddToCartView.as_view(), name="add-to-cart"),
    path('cart/remove/<slug:slug>/', api_views.RemoveFromCartView.as_view(), name="remove-from-cart"),
    path('customer/subscription/<uuid:uuid>/cancel/', api_views.SubscriptionCancelView.as_view(), name="customer-subscription-cancel"),
    path('authorizenet/authcapture', authorizenet_views.AuthroizeCaptureAPI.as_view(), name='api-authorizenet-authcapture-get')
]