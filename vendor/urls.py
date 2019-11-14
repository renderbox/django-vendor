from django.urls import path

from vendor import views

urlpatterns = [
    path('add-to-cart/', views.AddToCartView.as_view(), name="vendor-add-to-cart"),
    path('update/quantity/<str:sku>/increase/', views.IncreaseItemQuantityCartView.as_view(), name='vendor_increase-item-quantity'),
    path('update/quantity/<str:sku>/decrease/', views.RemoveSingleItemFromCartView.as_view(), name='vendor_remove-single-item-from-cart'),
    path('removefromcart/<str:sku>/', views.RemoveFromCartView.as_view(), name="vendor-remove-from-cart"),
    path('retrieve/cart/', views.RetrieveCartView.as_view(), name='vendor-user-cart-retrieve'),
    path('delete/cart/<int:id>/', views.DeleteCartView.as_view(), name='vendor-user-cart-delete'),
    path('retrieve/purchases/', views.RetrievePurchasesView.as_view(), name='vendor-user-purchases-retrieve'),
    path('retrieve/order-summary/', views.RetrieveOrderSummaryView.as_view(), name='vendor-order-summary-retrieve'),
    path('payment/processing/', views.PaymentProcessingView.as_view(), name='vendor-payment-processing'),
    path('request/refund/<int:id>/', views.RequestRefundView.as_view(), name='vendor-request-refund'),
    path('retrieve/refund/requests/', views.RetrieveRefundRequestsView.as_view(), name='vendor-retrieve-refund-requests'),
    path('issue/refund/<int:id>/', views.IssueRefundView.as_view(), name='vendor-issue-refund'),

]
