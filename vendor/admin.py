from django.contrib import admin

from vendor.models import TaxClassifier, Offer, Price, CustomerProfile, \
    Invoice, OrderItem, Receipt, Wishlist, WishlistItem, Address, Payment


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
    readonly_fields = ('uuid', 'profile', 'shipping_address')
    list_display = ('__str__', 'profile', 'site', 'status', 'created')
    inlines = [
        OrderItemInline,
    ]


class OfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('name', 'slug', 'site', 'terms', 'available')
    search_fields = ('name', 'site', )
    inlines = [
        PriceInline,
    ]


class PaymentAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'invoice', 'created', 'transaction', 'amount', 'profile', )
    list_display = ('created', 'transaction', 'invoice', 'profile', 'amount')
    search_fields = ('transaction', 'profile__user__username', )
    exclude = ('billing_address', )


class ReceiptAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'profile', 'order_item', 'created')
    exclude = ('updated', )
    list_display = ('transaction', 'created', 'profile', 'order_item', 'status', )
    search_fields = ('transaction', 'profile__user__username', )


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
