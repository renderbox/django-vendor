from django.urls import path

from vendor.views import admin as admin_views

app_name = "vendor"

urlpatterns = [
    path('manage/', admin_views.AdminDashboardView.as_view(), name="manager-dashboard"),
    path('manage/orders/', admin_views.AdminInvoiceListView.as_view(), name="manager-order-list"),
    path('manage/order/<uuid:uuid>/', admin_views.AdminInvoiceDetailView.as_view(), name="manager-order-detail"),
]
