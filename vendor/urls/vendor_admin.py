from django.urls import path

from vendor.views import vendor_admin as admin_views

app_name = "vendor_admin"

urlpatterns = [
    path('manage/', admin_views.AdminDashboardView.as_view(), name="manager-dashboard"),
    path('manage/products/', admin_views.AdminProductListView.as_view(), name="manager-product-list"),
    path('manage/product/<uuid:uuid>/', admin_views.AdminProductUpdateView.as_view(), name="manager-product-update"),
    path('manage/product/', admin_views.AdminProductCreateView.as_view(), name="manager-product-create"),
    path('manage/offers/', admin_views.AdminOfferListView.as_view(), name="manager-offer-list"),
    path('manage/offer/<uuid:uuid>/', admin_views.AdminOfferUpdateView.as_view(), name="manager-offer-update"),
    path('manage/offer/', admin_views.AdminOfferCreateView.as_view(), name="manager-offer-create"),
    path('manage/orders/', admin_views.AdminInvoiceListView.as_view(), name="manager-order-list"),
    path('manage/order/<uuid:uuid>/', admin_views.AdminInvoiceDetailView.as_view(), name="manager-order-detail"),
]
