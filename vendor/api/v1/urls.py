from django.urls import path

from vendor.api.v1 import views as api_views
from vendor.api.v1.authorizenet import views as authorizenet_views
from vendor.api.v1.stripe import views as stripe_views

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
    # AuthorizeNet
    path('authorizenet/authcapture', authorizenet_views.AuthorizeCaptureAPI.as_view(), name='api-authorizenet-authcapture'),
    path('authorizenet/void', authorizenet_views.VoidAPI.as_view(), name='api-authorizenet-void'),
    path('authorizenet/sync/subscriptions/', authorizenet_views.SyncSubscriptionsView.as_view(), name='api-authorizenet-sync-subscriptions'),
    path('authorizenet/settled/transactions/', authorizenet_views.GetSettledTransactionsView.as_view(), name='api-authorizenet-settled-transactions'),
    # Stripe
    path('stripe/invoice/paid/', stripe_views.StripeInvoicePaid.as_view(), name='api-stripe-invoice-paid'),
    path('stripe/subscription/invoice/paid/', stripe_views.StripeSubscriptionInvoicePaid.as_view(), name='api-stripe-subscription-invoice-paid'),
    path('stripe/subscription/invoice/payment/failed/', stripe_views.StripeSubscriptionPaymentFailed.as_view(), name='api-stripe-subscription-invoice-payment-failed'),
    path('stripe/sync/objects/', stripe_views.StripeSyncObjects.as_view(), name='api-stripe-sync-objects'),
    path('stripe/card/expiring/', stripe_views.StripeCardExpiring.as_view(), name='api-stripe-card-expiring'),
]