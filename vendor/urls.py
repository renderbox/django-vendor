from django.urls import path

from vendor import views

urlpatterns = [
    path("", views.VendorIndexView.as_view(), name="vendor_index"),
    path('add-to-cart/', views.AddToCartView.as_view(), name="add_to_cart"),
    path('update/quantity/<str:sku>/increase/', views.IncreaseItemQuantityCartView.as_view(), name='increase-item-quantity'),
    path('update/quantity/<str:sku>/decrease/', views.RemoveSingleItemFromCartView.as_view(), name='remove-single-item-from-cart'),
    path('removefromcart/<str:sku>/', views.RemoveFromCartView.as_view(), name="remove_from_cart"),
    path('retrieve/cart/', views.RetrieveCartView.as_view(), name='vendor-user-cart-retrieve'),
    path('delete/cart/<int:id>/', views.DeleteCartView.as_view(), name='vendor-user-cart-delete'),
    path('retrieve/purchases/', views.RetrievePurchasesView.as_view(), name='vendor-user-purchases-retrieve'),
    path('retrieve/order-summary/', views.RetrieveOrderSummaryView.as_view(), name='vendor-order-summary-retrieve'),
]
