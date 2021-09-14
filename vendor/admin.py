import logging

from django.contrib import admin
from django.db.models import Count

from vendor.models import TaxClassifier, Offer, Price, CustomerProfile, \
    Invoice, OrderItem, Receipt, Wishlist, WishlistItem, Address, Payment

logger = logging.getLogger(__name__)


################
# ADMIN ACTIONS
################
def soft_delete_payments_with_no_receipt(modeladmin, request, queryset):
    '''
    This action finds any successfull payment that has not a receipt that matches its transaction and created fields, and soft deletes them.
    Every successfull payment has a receipt that has the same transaction value.
    '''
    invalid_payments = [payment for payment in Payment.objects.filter(success=True) if payment.get_receipt() is None]

    for payment in invalid_payments:
        payment.delete()

    logger.info(f"Soft deleted {len(invalid_payments)} payments")


def soft_delete_payments_without_order_items_invoice(modeladmin, request, queryset):
    '''
    This action finds any successfull payment that with an invoice that has no order_items.
    Meaning it is a useless payment as it did not pay for any item
    '''
    invalid_payments = Payment.objects.filter(success=True).annotate(order_item_count=Count('invoice__order_items')).filter(order_item_count=0)
    for payment in invalid_payments:
        payment.delete()

    logger.info(f"Soft deleted {len(invalid_payments)} payments")


def soft_delete_invoices_with_deleted_payments(modeladmin, request, queryset):
    '''
    This action finds any invoice that has a status greater then Checkout and has a soft deleted payment.
    If an invoice has two payments, both need to be deleted to delete the invoice.
    '''
    for invoice in Invoice.objects.filter(status__gt=Invoice.InvoiceStatus.CHECKOUT):
        soft_delete = True
        for payment in invoice.payments.all():
            if not payment.deleted:
                soft_delete = False

        if soft_delete:
            invoice.delete()


soft_delete_payments_with_no_receipt.short_description = "Soft Delete Payments with no receipt"

soft_delete_payments_without_order_items_invoice.short_description = "Soft Delete Payments with zero order_items"

soft_delete_invoices_with_deleted_payments.short_description = "Soft Delete Invoices with payments that have been soft deleted"


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
    list_display = ('__str__', 'profile', 'site', 'status', 'total', 'created', 'deleted')
    search_fields = ('uuid', 'profile__user__username', )
    list_filter = ('site__domain', )
    inlines = [
        OrderItemInline,
    ]
    actions = [soft_delete_invoices_with_deleted_payments]


class OfferAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('name', 'slug', 'site', 'terms', 'available', 'deleted')
    search_fields = ('name', 'site', )
    list_filter = ('site__domain', )
    inlines = [
        PriceInline,
    ]


class PaymentAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'invoice', 'profile', )
    list_display = ('pk', 'created', 'transaction', 'invoice', 'profile', 'amount', 'deleted')
    search_fields = ('pk', 'transaction', 'profile__user__username', )
    list_filter = ('profile__site__domain', 'success')
    exclude = ('billing_address', )
    actions = [soft_delete_payments_without_order_items_invoice, soft_delete_payments_with_no_receipt]


class ReceiptAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'profile', 'order_item',)
    exclude = ('updated', )
    list_display = ('pk', 'transaction', 'created', 'profile', 'order_item', 'status', 'start_date', 'end_date', 'deleted')
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
