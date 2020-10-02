from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext as _
from .base import CreateUpdateModelBase
from .choice import CURRENCY_CHOICES, TermType
from .invoice import Invoice
from .utils import set_default_site_id
from vendor.config import DEFAULT_CURRENCY

#####################
# CUSTOMER PROFILE
#####################

class CustomerProfile(CreateUpdateModelBase):
    '''
    Additional customer information related to purchasing.
    This is what the Invoices are attached to.  This is abstracted from the user model directly do it can be mre flexible in the future.
    '''
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("User"), null=True, on_delete=models.SET_NULL, related_name="customer_profile")
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=DEFAULT_CURRENCY)      # User's default currency
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=set_default_site_id, related_name="customer_profile")                      # For multi-site support

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        verbose_name = _("Customer Profile")
        verbose_name_plural = _("Customer Profiles")

    def __str__(self):
        return "{} Customer Profile".format(self.user.username)

    def get_cart(self):
        cart, created = self.invoices.get_or_create(status=Invoice.InvoiceStatus.CART)
        return cart

    def has_product(self, product):
        """
        returns true/false if the user has a receipt to a given product
        it also checks against elegibility start/end/empty dates on consumable products and subscriptions
        """        
        now = timezone.now()

        count = self.receipts.filter( Q(products=product),
                              Q(start_date__lte=now) | Q(start_date=None),
                              Q(end_date__gte=now) | Q(end_date=None)).count() 

        if count:
            return True
        
        return False

    def get_cart_items_count(self):
        invoices = self.invoices.filter(site=Site.objects.get_current(), status=Invoice.InvoiceStatus.CART)

        if invoices:
            cart = invoices.all().first()
        else:
            cart = self.get_cart()

        return cart.order_items.all().count()

