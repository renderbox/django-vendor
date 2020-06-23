from django.contrib import admin

from vendor.models import Offer, Invoice, OrderItem

###############
# INLINES
###############

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

###############
# MODEL ADMINS
###############

class OfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)


class InvoiceAdmin(admin.ModelAdmin):
    inlines = [
        OrderItemInline,
    ]

###############
# REGISTRATION
###############

admin.site.register(Offer, OfferAdmin)
admin.site.register(Invoice, InvoiceAdmin)


