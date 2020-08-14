from django.contrib import admin

from vendor.models import TaxClassifier, Offer, Price, CustomerProfile, \
                    Invoice, OrderItem, Reciept, Wishlist, WishlistItem

###############
# INLINES
###############

class RecieptInline(admin.TabularInline):
    model = Reciept
    extra = 1


class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 1


class WishlistInline(admin.TabularInline):
    model = Wishlist
    extra = 1


class PriceInline(admin.TabularInline):
    model = Price
    extra = 1


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 1

###############
# MODEL ADMINS
###############

class TaxClassifierAdmin(admin.ModelAdmin):
    pass


class CustomerProfileAdmin(admin.ModelAdmin):
    inlines = [
        RecieptInline,
        InvoiceInline,
        WishlistInline,
    ]


class OfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    inlines = [
        PriceInline,
    ]


class InvoiceAdmin(admin.ModelAdmin):
    inlines = [
        OrderItemInline,
    ]


class WishlistAdmin(admin.ModelAdmin):
    inlines = [
        WishlistItemInline,
    ]

###############
# REGISTRATION
###############

admin.site.register(TaxClassifier, TaxClassifierAdmin)
admin.site.register(CustomerProfile, CustomerProfileAdmin)
admin.site.register(Offer, OfferAdmin)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(Wishlist, WishlistAdmin)


