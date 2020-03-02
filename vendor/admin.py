from django.contrib import admin

from vendor.models import ProductOffer, Invoice, OrderItem

###############
# INLINES
###############

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

###############
# MODEL ADMINS
###############

class ProductOfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)


class InvoiceAdmin(admin.ModelAdmin):
    inlines = [
        OrderItemInline,
    ]

###############
# REGISTRATION
###############

admin.site.register(ProductOffer, ProductOfferAdmin)
admin.site.register(Invoice, InvoiceAdmin)


