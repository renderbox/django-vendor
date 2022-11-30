from django.urls import path

from vendor.views import vendor_admin as admin_views
from vendor.views import report as report_views

app_name = "vendor_admin"

urlpatterns = [
    path('', admin_views.AdminDashboardView.as_view(), name="manager-dashboard"),
    path('products/', admin_views.AdminProductListView.as_view(), name="manager-product-list"),
    path('product/<uuid:uuid>/', admin_views.AdminProductUpdateView.as_view(), name="manager-product-update"),
    path('product/', admin_views.AdminProductCreateView.as_view(), name="manager-product-create"),
    path('offers/', admin_views.AdminOfferListView.as_view(), name="manager-offer-list"),
    path('offer/<uuid:uuid>/', admin_views.AdminOfferUpdateView.as_view(), name="manager-offer-update"),
    path('offer/', admin_views.AdminOfferCreateView.as_view(), name="manager-offer-create"),
    path('orders/', admin_views.AdminInvoiceListView.as_view(), name="manager-order-list"),
    path('order/<uuid:uuid>/', admin_views.AdminInvoiceDetailView.as_view(), name="manager-order-detail"),
    path('subscriptions/', admin_views.AdminSubscriptionListView.as_view(), name="manager-subscriptions"),
    path('subscription/<uuid:uuid>', admin_views.AdminSubscriptionDetailView.as_view(), name="manager-subscription"),
    path('subscription/<uuid:uuid_subscription>/add/payment/<uuid:uuid_profile>/', admin_views.AdminSubscriptionAddPaymentView.as_view(), name="manager-subscription-add-payment"),
    path('subscription/create/', admin_views.AdminSubscriptionCreateView.as_view(), name="manager-subscription-create"),
    path('profiles/', admin_views.AdminProfileListView.as_view(), name="manager-profiles"),
    path('profile/<uuid:uuid>', admin_views.AdminProfileDetailView.as_view(), name="manager-profile"),
    path('product/<uuid:uuid>/renew', admin_views.AdminManualSubscriptionRenewal.as_view(), name="manager-product-renew"),
    path('payments/no/receipt/', admin_views.PaymentWithNoReceiptListView.as_view(), name="manager-payment-no-receipt"),
    path('payments/no/orderitems/', admin_views.PaymentWithNoOrderItemsListView.as_view(), name="manager-payment-no-receipt"),
    path("processors/", admin_views.PaymentProcessorSiteConfigsListView.as_view(), name="vendor-processor-lists"),
    path("processor/site/", admin_views.PaymentProcessorSiteFormView.as_view(), name="vendor-site-processor"),
    path("processor/new/site/", admin_views.PaymentProcessorSiteSelectFormView.as_view(), name="vendor-new-site-processor"),
    path("processor/edit/<domain>/site/processors/", admin_views.PaymentProcessorSiteSelectFormView.as_view(), name="vendor-sites-processors"),
    path("authorizenet/integration/", admin_views.AuthorizeNetIntegrationView.as_view(), name="authorizenet-integration"),
    path("stripe/integration/", admin_views.StripeIntegrationView.as_view(), name="stripe-integration"),

    # reports
    path('reports/receipts/download/', report_views.ReceiptListCSV.as_view(), name="manager-receipt-download"),
    path('reports/invoices/download/', report_views.InvoiceListCSV.as_view(), name="manager-invoice-download"),
]
