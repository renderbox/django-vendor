from django.urls import path

from core import views

urlpatterns = [
    path("", views.VendorIndexView.as_view(), name="vendor_index"),
    path("product/<slug:slug>/access/", views.ProductAccessView.as_view(), name="product-access"),
    path("account/", views.AccountView.as_view(), name="account"),
    path("logger/test/", views.LoggerTestView.as_view(), name='test-logger')
]
