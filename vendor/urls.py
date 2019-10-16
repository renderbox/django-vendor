from django.urls import path

from vendor import views

urlpatterns = [
    path("", views.VendorIndexView.as_view(), name="vendor_index"),
    # path('add-to-cart/<str:sku>/', views.AddToCartView.as_view(), name="add_to_cart"),
    # path('remove-from-cart/<str:sku>/', views.RemoveFromCartView.as_view(), name="remove_from_cart"),
    # path('remove-single-item-from-cart/<str:sku>/', views.RemoveSingleItemFromCartView.as_view(), name="remove_single_item_from_cart")
]
