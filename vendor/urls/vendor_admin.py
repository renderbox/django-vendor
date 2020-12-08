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

    # reports
    path('reports/receipts/download/', report_views.ReceiptListCSV.as_view(), name="manager-receipt-download"),
    path('reports/invoices/download/', report_views.InvoiceListCSV.as_view(), name="manager-invoice-download"),
]
