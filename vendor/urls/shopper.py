from django.urls import path

from vendor.views import shopper as shopper_views

app_name = "vendor_shopper"

urlpatterns = [
    path('cart/', shopper_views.CartView.as_view(), name="cart"),
    path('cart/add/<slug:slug>/', shopper_views.AddToCartView.as_view(), name="add-to-cart"),
    path('cart/remove/<slug:slug>/', shopper_views.RemoveFromCartView.as_view(), name="remove-from-cart"),
    path('cart/summary/<uuid:uuid>/', shopper_views.PaymentView.as_view(), name="purchase-summary"),
    # path('cart/remove/<slug:slug>/', shopper_views.TransactionSummary.as_view(), name="transaction-summary"),
    # path('cart-item/edit/<int:id>/', shopper_views.CartItemQuantityEditView.as_view(), name='vendor-cart-item-quantity-edit'),
    # path('retrieve/cart/', shopper_views.RetrieveCartView.as_view(), name='vendor-user-cart-retrieve'),
    # path('delete/cart/<int:id>/', shopper_views.DeleteCartView.as_view(), name='vendor-user-cart-delete'),
    # path('retrieve/order/<int:id>/', shopper_views.RetrieveOrderView.as_view(), name='vendor-user-order-retrieve'),
    # path('retrieve/purchase-item/<int:id>/', shopper_views.RetrievePurchaseView.as_view(), name='vendor-user-purchase-retrieve'),
    # path('retrieve/purchase/list/', shopper_views.RetrievePurchaseListView.as_view(), name='vendor-user-purchase-list'),
    # path('retrieve/order-summary/', shopper_views.RetrieveOrderSummaryView.as_view(), name='vendor-order-summary-retrieve'),
    # path('payment/processing/', shopper_views.PaymentProcessingView.as_view(), name='vendor-payment-processing'),
    # path('request/refund/<int:id>/', shopper_views.RequestRefundView.as_view(), name='vendor-request-refund'),
    # path('retrieve/refund/requests/', shopper_views.RetrieveRefundRequestsView.as_view(), name='vendor-retrieve-refund-requests'),
    # path('issue/refund/<int:id>/', shopper_views.IssueRefundView.as_view(), name='vendor-issue-refund'),
    path('checkout/', shopper_views.CheckoutView.as_view(), name="checkout"),
]
