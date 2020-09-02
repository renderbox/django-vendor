from django.urls import path

from vendor import views

app_name = "vendor"

urlpatterns = [
    path('cart/', views.CartView.as_view(), name="cart"),
    path('cart/add/<slug:slug>/', views.AddToCartView.as_view(), name="add-to-cart"),
    path('cart/remove/<slug:slug>/', views.RemoveFromCartView.as_view(), name="remove-from-cart"),
    path('cart/payment/<int:pk>/', views.PaymentView.as_view(), name="purchase-summary"),
    # path('cart/remove/<slug:slug>/', views.TransactionSummary.as_view(), name="transaction-summary"),
    # path('cart-item/edit/<int:id>/', views.CartItemQuantityEditView.as_view(), name='vendor-cart-item-quantity-edit'),
    # path('retrieve/cart/', views.RetrieveCartView.as_view(), name='vendor-user-cart-retrieve'),
    # path('delete/cart/<int:id>/', views.DeleteCartView.as_view(), name='vendor-user-cart-delete'),
    # path('retrieve/order/<int:id>/', views.RetrieveOrderView.as_view(), name='vendor-user-order-retrieve'),
    # path('retrieve/purchase-item/<int:id>/', views.RetrievePurchaseView.as_view(), name='vendor-user-purchase-retrieve'),
    # path('retrieve/purchase/list/', views.RetrievePurchaseListView.as_view(), name='vendor-user-purchase-list'),
    # path('retrieve/order-summary/', views.RetrieveOrderSummaryView.as_view(), name='vendor-order-summary-retrieve'),
    # path('payment/processing/', views.PaymentProcessingView.as_view(), name='vendor-payment-processing'),
    # path('request/refund/<int:id>/', views.RequestRefundView.as_view(), name='vendor-request-refund'),
    # path('retrieve/refund/requests/', views.RetrieveRefundRequestsView.as_view(), name='vendor-retrieve-refund-requests'),
    # path('issue/refund/<int:id>/', views.IssueRefundView.as_view(), name='vendor-issue-refund'),
    path('checkout/', views.CheckoutView.as_view(), name="checkout"),
    
    path('orders/', views.OrderHistoryListView.as_view(), name="order-list"),
    path('order/<uuid:uuid>/', views.OrderHistoryDetailView.as_view(), name="order-detail"),

    path('manage/', views.AdminDashboardView.as_view(), name="manager-dashboard"),
    path('manage/orders/', views.AdminInvoiceListView.as_view(), name="manager-order-list"),
    path('manage/order/<uuid:uuid>/', views.AdminInvoiceDetailView.as_view(), name="manager-order-detail"),
]
