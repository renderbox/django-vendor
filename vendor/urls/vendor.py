from django.urls import path

from vendor.views import vendor as vendor_views

app_name = "vendor"

urlpatterns = [
    path('', vendor_views.VendorHomeView.as_view(), name='vendor-home'),
    path('cart/', vendor_views.CartView.as_view(), name="cart"),
    path('checkout/summary/<uuid:uuid>/', vendor_views.PaymentSummaryView.as_view(), name="purchase-summary"),

    path('checkout/account/', vendor_views.AccountInformationView.as_view(), name="checkout-account"),
    path('checkout/payment/', vendor_views.PaymentView.as_view(), name="checkout-payment"),
    path('checkout/review/', vendor_views.ReviewCheckoutView.as_view(), name="checkout-review"),

    path('customer/products/', vendor_views.ReceiptListView.as_view(), name="customer-products"),
    path('customer/product/<uuid:uuid>/receipt/', vendor_views.ReceiptDetailView.as_view(), name="customer-receipt"),
    path('customer/subscriptions/', vendor_views.SubscriptionsListView.as_view(), name="customer-subscriptions"),
    path('customer/subscription/update/<uuid:uuid>/payment', vendor_views.SubscriptionUpdatePaymentView.as_view(), name="customer-subscription-update-payment"),
    path('customer/shipping/<uuid:uuid>/update', vendor_views.ShippingAddressUpdateView.as_view(), name="customer-shipping-update"),               # TODO: [GK-3030] Do not use PKs in URLs
    path('customer/billing/<uuid:uuid>/update', vendor_views.AddressUpdateView.as_view(), name="customer-billing-update"),

    # TODO: Add user's account mangement urls
    # TODO: add user's order details page
]
