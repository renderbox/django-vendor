from django.urls import path

from vendor import views

urlpatterns = [
    path("", views.VendorIndexView.as_view(), name="vendor_index"),
]
