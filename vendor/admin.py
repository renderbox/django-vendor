from django.contrib import admin

# Register your models here.
# from vendor.models import Catalog, Price, Invoice, OrderItem
from vendor.models import Price, Invoice, OrderItem, Offer, Purchases, CustomerProfile

# admin.site.register(Catalog)
admin.site.register(Offer)
admin.site.register(Price)
admin.site.register(Invoice)
admin.site.register(OrderItem)
admin.site.register(Purchases)
admin.site.register(CustomerProfile)
