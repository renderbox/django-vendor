from django.urls import path

from core import views

urlpatterns = [
    path("", views.VendorIndexView.as_view(), name="vendor_index"),
]
