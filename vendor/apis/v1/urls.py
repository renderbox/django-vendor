from django.urls import path

from vendor.apis.v1 import views as api_views
from vendor.apis.v1.authorizenet import views as authorizenet_views

app_name = "vendor_api"

urlpatterns = [
    path('', api_views.VendorIndexAPI.as_view(), name='api-index'),
    path('authorizenet/authcapture/', authorizenet_views.AuthroizeCaptureAPI.as_view(), name='api-authorizenet-authcapture-get')
]