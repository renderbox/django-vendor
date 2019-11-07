from django.urls import path

from vendor.api import views

urlpatterns = [
    # path('samplemodel/list/', views.SampleModelListAPIView.as_view(), name='sample-model-list'),
    path('addtocart/', views.AddToCartAPIView.as_view(), name='vendor-add-to-cart-api'),
    path('update/quantity/<str:sku>/decrease/', views.RemoveSingleItemFromCartAPIView.as_view(), name='remove-single-item-from-cart-api'),
    path('update/quantity/<str:sku>/increase/', views.IncreaseItemQuantityCartAPIView.as_view(), name='increase-item-quantity-api'),
    path('removefromcart/<str:sku>/', views.RemoveFromCartAPIView.as_view(), name='remove-from-cart-api'),
    path('retrieve/cart/', views.RetrieveCartAPIView.as_view(), name='vendor-user-cart-retrieve-api'),
    path('delete/cart/', views.DeleteCartAPIView.as_view(), name='vendor-user-cart-delete-api'),
    path('retrieve/purchases/', views.RetrievePurchasesAPIView.as_view(), name='vendor-purchases-retrieve-api'),
    path('retrieve/order/summary/', views.RetrieveOrderSummaryAPIView.as_view(), name='vendor-order-summary-retrieve-api'),

]
