import uuid

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.db import models
from django.utils.translation import ugettext as _


from .base import CreateUpdateModelBase
from .choice import CURRENCY_CHOICES
from .utils import set_default_site_id
from vendor.config import DEFAULT_CURRENCY

#####################
# INVOICE
#####################

class Invoice(CreateUpdateModelBase):
    '''
    An invoice starts off as a Cart until it is puchased, then it becomes an Invoice.
    '''
    class InvoiceStatus(models.IntegerChoices):
        CART = 0, _("Cart")             # total = subtotal = sum(OrderItems.Offer.Price + Product.TaxClassifier). Avalara
        CHECKOUT = 10, _("Checkout")    # total = subtotal + shipping + Tax against Addrr if any.
        QUEUED = 20, _("Queued")        # Queued to for Payment Processor.
        PROCESSING = 30, _("Processing")# Payment Processor update, start of payment.
        FAILED = 40, _("Failed")        # Payment Processor Failed Transaction.
        COMPLETE = 50, _("Complete")    # Payment Processor Completed Transaction.
        REFUNDED = 60, _("Refunded")    # Invoice Refunded to client. 

    uuid = models.UUIDField(_("UUID"), default=uuid.uuid4, editable=False, unique=True)
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Customer Profile"), null=True, on_delete=models.CASCADE, related_name="invoices")
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=set_default_site_id, related_name="invoices")                      # For multi-site support
    status = models.IntegerField(_("Status"), choices=InvoiceStatus.choices, default=InvoiceStatus.CART)
    customer_notes = models.JSONField(_("Customer Notes"), default=dict, blank=True, null=True)
    vendor_notes = models.JSONField(_("Vendor Notes"), default=dict, blank=True, null=True)
    ordered_date = models.DateTimeField(_("Ordered Date"), blank=True, null=True)               # When was the purchase made?
    subtotal = models.FloatField(default=0.0)                                   
    tax = models.FloatField(blank=True, null=True)                              # Set on checkout
    shipping = models.FloatField(blank=True, null=True)                         # Set on checkout
    total = models.FloatField(blank=True, null=True)                            # Set on purchase
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=DEFAULT_CURRENCY)      # User's default currency
    shipping_address = models.ForeignKey("vendor.Address", verbose_name=_("Shipping Address"), on_delete=models.CASCADE, blank=True, null=True)
    # paid = models.BooleanField(_("Paid"))                 # May be Useful for quick filtering on invoices that are outstanding
    # settle_date = models.DateTimeField(_("Settle Date"))

    objects = models.Manager()
    on_site = CurrentSiteManager()


    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ['-ordered_date', '-updated']             # TODO: [GK-2518] change to use ordered_date.  Invoice ordered_date needs to be updated on successful purchase by the PaymentProcessor.

        permissions = (
            ('can_view_site_purchases', 'Can view Site Purchases'),
            ('can_refund_purchase', 'Can refund Purchase'),
        )

    def __str__(self):
        return "%s Invoice (%s)" % (self.profile.user.username, self.created.strftime('%Y-%m-%d %H:%M'))

    def add_offer(self, offer):
        order_item, created = self.order_items.get_or_create(offer=offer)
        # make sure the invoice pk is also in the OriderItem
        if not created:
            order_item.quantity += 1
            order_item.save()

        self.update_totals()
        self.save()
        return order_item

    def remove_offer(self, offer):
        try:
            order_item = self.order_items.get(offer=offer)      # Get the order item if it's present
        except:
            return 0

        order_item.quantity -= 1

        if order_item.quantity == 0:
            order_item.delete()
        else:
            order_item.save()

        self.update_totals()
        self.save()
        return order_item

    def calculate_shipping(self):
        '''
        Based on the Shipping Address
        '''
        self.shipping = 0

    def calculate_tax(self):
        '''
        Extendable
        '''
        self.tax = 0

    def update_totals(self):
        self.subtotal = sum([item.total for item in self.order_items.all() ])

        self.calculate_shipping()
        self.calculate_tax()
        self.total = self.subtotal + self.tax + self.shipping

    def get_payment_billing_address(self):
        return self.payments.get(success=True).billing_address.get_address()


class OrderItem(CreateUpdateModelBase):
    '''
    A link for each item to a user after it's been purchased
    '''
    invoice = models.ForeignKey("vendor.Invoice", verbose_name=_("Invoice"), on_delete=models.CASCADE, related_name="order_items")
    offer = models.ForeignKey("vendor.Offer", verbose_name=_("Offer"), on_delete=models.CASCADE, related_name="order_items")
    quantity = models.IntegerField(_("Quantity"), default=1)

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    def __str__(self):
        return "%s - %s" % (self.invoice.profile.user.username, self.offer.name)

    @property
    def total(self):
        return self.quantity * self.price

    @property
    def price(self):
        return self.offer.current_price()

    @property
    def name(self):
        return self.offer.name

