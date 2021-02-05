from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib import admin

from vendor.models import TaxClassifier, Offer, Price, CustomerProfile, \
    Invoice, OrderItem, Receipt, Wishlist, WishlistItem, Address, Payment

from vendor.config import VENDOR_PRODUCT_MODEL

###############
# INLINES
###############


class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 1


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class PriceInline(admin.TabularInline):
    model = Price
    extra = 1


class ReceiptInline(admin.TabularInline):
    model = Receipt
    extra = 1


class WishlistInline(admin.TabularInline):
    model = Wishlist
    extra = 1


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 1

###############
# MODEL ADMINS
###############


class AddressAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('name', 'profile', 'postal_code')


class CustomerProfileAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('user', 'site', 'currency')
    inlines = [
        ReceiptInline,
        InvoiceInline
    ]


class InvoiceAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('__str__', 'profile', 'site', 'status', 'created')
    inlines = [
        OrderItemInline,
    ]


class OfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('name', 'site')
    inlines = [
        PriceInline,
    ]


class PaymentAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('__str__', 'transaction', 'invoice', 'profile', 'amount')


class ReceiptAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('__str__', 'transaction', 'profile', 'order_item', 'status')


class TaxClassifierAdmin(admin.ModelAdmin):
    pass


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
admin.site.register(Address, AddressAdmin)
admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(OrderItem)
