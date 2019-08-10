from django.contrib import admin

# Register your models here.
from vendor.models import Catalog, Price, Order, OrderItem

admin.site.register(Catalog)
admin.site.register(Price)
admin.site.register(Order)
admin.site.register(OrderItem)
