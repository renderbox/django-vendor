from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib import admin

from vendor.models import TaxClassifier, Offer, Price, CustomerProfile, \
                    Invoice, OrderItem, Receipt, Wishlist, WishlistItem, Address

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
    inlines = [
        ReceiptInline,
        InvoiceInline,
        WishlistInline,
    ]

class OfferAdminForm(forms.ModelForm):
    
    def clean_name(self):
        product_model = apps.get_model(settings.VENDOR_PRODUCT_MODEL)
        name = self.cleaned_data['name']
        bundle = self.data.getlist('bundle')
        
        if len(self.data.getlist('bundle')) == 1:
            return product_model.objects.get(pk=bundle[0]).name
        else:
            return "Bundle: " + ",".join( [ qs.name for qs in product_model.objects.filter(pk__in=bundle) ] )

class OfferAdmin(admin.ModelAdmin):
    # TODO: Only show active Product in new Offers or change Offers
    readonly_fields = ('uuid',)
    inlines = [
        PriceInline,
    ]
    form = OfferAdminForm


      
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


