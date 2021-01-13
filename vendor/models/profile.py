import uuid

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from .base import CreateUpdateModelBase
from .choice import CURRENCY_CHOICES, TermType, PurchaseStatus
from .invoice import Invoice
from .utils import set_default_site_id
from vendor.config import DEFAULT_CURRENCY

from vendor.config import DEFAULT_CURRENCY

from vendor.models.base import get_product_model

#####################
# CUSTOMER PROFILE
#####################


class CustomerProfile(CreateUpdateModelBase):
    '''
    Additional customer information related to purchasing.
    This is what the Invoices are attached to.  This is abstracted from the user model directly do it can be mre flexible in the future.
    '''
    uuid = models.UUIDField(_("UUID"), editable=False, unique=True, default=uuid.uuid4, null=False, blank=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("User"), null=True, on_delete=models.SET_NULL, related_name="customer_profile")
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES,default=DEFAULT_CURRENCY)      # User's default currency
    site = models.ForeignKey(Site, verbose_name=_("Site"), on_delete=models.CASCADE, default=set_default_site_id, related_name="customer_profile")                      # For multi-site support

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"

    def __str__(self):
        if not self.user:
            return "New Customer Profile"
        return "{username} Customer Profile".format(username=self.user.username)

    def get_customer_profile_display(self):
        return str(self.user.username) + _("Customer Profile")

    def revert_invoice_to_cart(self):
        cart = self.invoices.get(status=Invoice.InvoiceStatus.CHECKOUT)
        cart.status = Invoice.InvoiceStatus.CART
        cart.save()

    def get_cart(self):
        if self.has_invoice_in_checkout():
            self.revert_invoice_to_cart()
        cart, created = self.invoices.get_or_create(status=Invoice.InvoiceStatus.CART)
        return cart

    def get_checkout_cart(self):
        return self.invoices.filter(status=Invoice.InvoiceStatus.CHECKOUT).first()

    def get_cart_or_checkout_cart(self):
        carts_status = [cart.status for cart in self.invoices.filter(status__in=[Invoice.InvoiceStatus.CHECKOUT, Invoice.InvoiceStatus.CART])]
        
        if Invoice.InvoiceStatus.CHECKOUT in carts_status:
            return self.invoices.get(status=Invoice.InvoiceStatus.CHECKOUT)
        else:
            cart, created = self.invoices.get_or_create(status=Invoice.InvoiceStatus.CART)
            return cart
    
    def has_invoice_in_checkout(self):
        return bool(self.invoices.filter(status=Invoice.InvoiceStatus.CHECKOUT).count())
        
    def filter_products(self, products):
        """
        returns the list of receipts that the user has a receipt for filtered by the products provided.
        """
        now = timezone.now()

        # Queryset or List of model records
        if isinstance(products, QuerySet) or isinstance(products, list):
            return self.receipts.filter(Q(products__in=products),
                                Q(start_date__lte=now) | Q(start_date=None),
                                Q(end_date__gte=now) | Q(end_date=None))

        # Single model record
        return self.receipts.filter(Q(products=products),
                                Q(start_date__lte=now) | Q(start_date=None),
                                Q(end_date__gte=now) | Q(end_date=None))

    def has_product(self, products):
        """
        returns true/false if the user has a receipt to a given product(s)
        it also checks against elegibility start/end/empty dates on consumable products and subscriptions
        """
        return bool(self.filter_products(products).count())
    
    def get_recurring_receipts(self):
        """
        Gets the recurring receipts the customer profile might have
        """
        return self.receipts.filter(order_item__offer__terms__lt=TermType.PERPETUAL)

    def get_one_time_transaction_receipts(self):
        """
        Gets one time transation receipt the customer profile might have
        """
        return self.receipts.filter(order_item__offer__terms__gte=TermType.PERPETUAL)

    def get_cart_items_count(self):
        cart = self.get_cart_or_checkout_cart()

        return cart.order_items.all().count()

    def get_or_create_address(self, address):
        address, created = self.addresses.get_or_create(name=address.address_1, first_name=address.first_name, last_name=address.last_name, address_1=address.address_1, address_2=address.address_2, locality=address.locality, state=address.state, country=address.country, postal_code=address.postal_code, profile=self)
        return address, created

    def has_previously_owned_products(self, products):
        """
        Get all products that the customer has purchased and returns True if it has.
        """
        return bool(self.receipts.filter(products__in=products, status__gte=PurchaseStatus.COMPLETE).first())
    
    def get_customer_products(self):
        Product = get_product_model()
        return Product.objects.filter(receipts__profile=self)

    def get_completed_receipts(self):
        return self.receipts.filter(status__gte=PurchaseStatus.COMPLETE)
