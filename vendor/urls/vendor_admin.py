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
    path('profiles/', admin_views.AdminProfileListView.as_view(), name="manager-profiles"),
    path('profile/<uuid:uuid>', admin_views.AdminProfileDetailView.as_view(), name="manager-profile"),
    path('profile/<uuid:uuid_profile>/offer/<uuid:uuid_offer>/add', admin_views.AddOfferToProfileView.as_view(), name="manager-profile-add-offer"),
    path('product/<uuid:uuid>/remove', admin_views.VoidProductView.as_view(), name="manager-profile-remove-product"),

    # reports
    path('reports/receipts/download/', report_views.ReceiptListCSV.as_view(), name="manager-receipt-download"),
    path('reports/invoices/download/', report_views.InvoiceListCSV.as_view(), name="manager-invoice-download"),
]