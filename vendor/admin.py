from django.contrib import admin

# Register your models here.
# from vendor.models import Catalog, Price, Invoice, OrderItem
from vendor.models import Price, Invoice, OrderItem, Offer, Purchase, CustomerProfile, Refund

###############
# MODEL ADMINS
###############

class OfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
   

###############
# REGISTRATION
###############

# admin.site.register(Catalog)
admin.site.register(Offer, OfferAdmin)
admin.site.register(Price)
admin.site.register(Invoice)
admin.site.register(OrderItem)
admin.site.register(Purchase)
admin.site.register(CustomerProfile)
admin.site.register(Refund)


