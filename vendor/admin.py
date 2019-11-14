from django.contrib import admin

from vendor.models import Price, Invoice, OrderItem, Offer, Purchase, CustomerProfile, Refund

###############
# INLINES
###############

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class PriceInline(admin.TabularInline):
    model = Price
    extra = 1


###############
# MODEL ADMINS
###############

class OfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    inlines = [
        PriceInline,
    ]

class InvoiceAdmin(admin.ModelAdmin):
    inlines = [
        OrderItemInline,
    ]

###############
# REGISTRATION
###############

admin.site.register(Offer, OfferAdmin)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(Purchase)
admin.site.register(CustomerProfile)
admin.site.register(Refund)


