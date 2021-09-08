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
    search_fields = ('postal_code', )


class CustomerProfileAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('user', 'site', 'currency')
    search_fields = ('profile__user__username', )
    list_filter = ('site__domain', )
    inlines = [
        ReceiptInline,
        InvoiceInline
    ]


class InvoiceAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'profile', 'shipping_address')
    list_display = ('__str__', 'profile', 'site', 'status', 'total', 'created')
    search_fields = ('profile__user__username', )
    list_filter = ('site__domain', )
    inlines = [
        OrderItemInline,
    ]


class OfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('name', 'slug', 'site', 'terms', 'available')
    search_fields = ('name', 'site', )
    list_filter = ('site__domain', )
    inlines = [
        PriceInline,
    ]


class PaymentAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'invoice', 'created', 'profile', )
    list_display = ('pk', 'created', 'transaction', 'invoice', 'profile', 'amount')
    search_fields = ('pk', 'transaction', 'profile__user__username', )
    list_filter = ('profile__site__domain', 'success')
    exclude = ('billing_address', )


class ReceiptAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'profile', 'order_item', 'created',)
    exclude = ('updated', )
    list_display = ('pk', 'transaction', 'created', 'profile', 'order_item', 'status', 'start_date', 'end_date')
    list_filter = ('profile__site__domain', 'status', 'products')
    search_fields = ('pk', 'transaction', 'profile__user__username', )


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
