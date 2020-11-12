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

class ReceiptInline(admin.TabularInline):
    model = Receipt
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
    # TODO: Revisit proper way of display Customer Profile on Admin Page.
    # inlines = [
    #     ReceiptInline,
    #     InvoiceInline,
    #     WishlistInline,
    # ]
    pass

# class OfferAdminForm(forms.ModelForm):
    # TODO: Proper validation for empty name needed
    # def clean_name(self):
    #     name = self.cleaned_data['name']
    #     if not name:
    #         product_names = [ product.name for product in self.products.all() ]
    #         if len(product_names) == 1:
    #             return product_names[0]
    #         else:
    #             return "Bundle: " + ", ".join(product_names)
                

class OfferAdmin(admin.ModelAdmin):
    # TODO: Only show active Product in new Offers or change Offers
    readonly_fields = ('uuid',)
    inlines = [
        PriceInline,
    ]
    # form = OfferAdminForm


      
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
admin.site.register(Address)
admin.site.register(Receipt)
admin.site.register(Payment)
admin.site.register(OrderItem)


