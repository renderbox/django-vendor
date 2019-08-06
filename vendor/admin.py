from django.contrib import admin

# Register your models here.
from vendor.models import Catalog, SalePrice, Cart, CartItem, Order, OrderItem

admin.site.register(Catalog)
admin.site.register(SalePrice)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
