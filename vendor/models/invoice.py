from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import ugettext as _

from .base import CreateUpdateModelBase
from .choice import CURRENCY_CHOICES

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

    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Customer Profile"), null=True, on_delete=models.CASCADE, related_name="invoices")
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=settings.SITE_ID, related_name="invoices")                      # For multi-site support
    status = models.IntegerField(_("Status"), choices=InvoiceStatus.choices, default=InvoiceStatus.CART)
    customer_notes = models.TextField(blank=True, null=True)
    vendor_notes = models.TextField(blank=True, null=True)
    ordered_date = models.DateTimeField(_("Ordered Date"), blank=True, null=True)               # When was the purchase made?
    subtotal = models.FloatField(default=0.0)                                   
    tax = models.FloatField(blank=True, null=True)                              # Set on checkout
    shipping = models.FloatField(blank=True, null=True)                         # Set on checkout
    total = models.FloatField(blank=True, null=True)                            # Set on purchase
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=settings.DEFAULT_CURRENCY)      # User's default currency
    shipping_address = models.ForeignKey("vendor.Address", verbose_name=_("Shipping Address"), on_delete=models.CASCADE, blank=True, null=True)
    # paid = models.BooleanField(_("Paid"))                 # May be Useful for quick filtering on invoices that are outstanding
    # paid_date = models.DateTimeField(_("Payment Date"))

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")

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


    # def save(self):
    #     pass
    # DEFAULT_CURRENCY


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
        # TODO: What if it is an Bundle
        return self.offer.product.name

