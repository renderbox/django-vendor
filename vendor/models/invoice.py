import itertools
import uuid

from allauth.account.signals import user_logged_in

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from vendor.models.utils import set_default_site_id
from vendor.config import DEFAULT_CURRENCY
from vendor.utils import get_site_from_request, get_subscription_start_date
from .base import CreateUpdateModelBase
from .choice import CURRENCY_CHOICES, TermType, InvoiceStatus
from .offer import Offer
from .base import SoftDeleteModelBase


#####################
# INVOICE
#####################
class Invoice(SoftDeleteModelBase, CreateUpdateModelBase):
    '''
    An invoice starts off as a Cart until it is puchased, then it becomes an Invoice.
    '''
    uuid = models.UUIDField(_("UUID"), default=uuid.uuid4, editable=False, unique=True)
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Customer Profile"), on_delete=models.CASCADE, related_name="invoices")
    site = models.ForeignKey(Site, verbose_name=_("Site"), on_delete=models.CASCADE, default=set_default_site_id, related_name="invoices")                      # For multi-site support
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

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ['-ordered_date', '-updated']             # TODO: [GK-2518] change to use ordered_date.  Invoice ordered_date needs to be updated on successful purchase by the PaymentProcessor.

        permissions = (
            ('can_view_site_purchases', 'Can view Site Purchases'),
            ('can_refund_purchase', 'Can refund Purchase'),
        )

    def __str__(self):
        if not self.profile.user:   # Can this ever even happen?
            return "New Invoice"
        return f"{self.profile.user.username} - {self.uuid}"

    def get_invoice_display(self):
        if self.profile.user.username is None:
            return _(f"Invoice ({self.created:%Y-%m-%d %H:%M})")
        return _(f"{self.profile.user.username} Invoice ({self.created:%Y-%m-%d %H:%M})")

    def add_offer(self, offer, quantity=1):

        order_item, created = self.order_items.get_or_create(offer=offer)
        
        # make sure the invoice pk is also in the OriderItem
        if not created and order_item.offer.allow_multiple:
            order_item.quantity += quantity
            order_item.save()

        self.update_totals()
        self.save()

        return order_item

    def remove_offer(self, offer, clear=False):
        try:
            order_item = self.order_items.get(offer=offer)      # Get the order item if it's present
        except ObjectDoesNotExist:
            return 0

        order_item.quantity -= 1

        if order_item.quantity == 0 or clear:
            order_item.delete()
        else:
            order_item.save()

        self.update_totals()
        self.save()
        return order_item

    def swap_offer(self, existing_offer, new_offer):
        """
        Functions swaps offers that have the same linked product. It will not remove bundle offers
        that also have shared product with the new offer. The function comes in handy to swap
        an offer that has the normal price with one that has a discount price or terms.
        """
        if not existing_offer.products.filter(pk__in=[offer.pk for offer in new_offer.products.all()]).exists():
            return None

        if self.order_items.filter(offer=existing_offer).exists():
            order_items_same_product = self.order_items.filter(offer=existing_offer).exclude(offer__bundle=True)
            for order_item in order_items_same_product:
                self.remove_offer(order_item.offer, clear=True)

        self.add_offer(new_offer)
        self.update_totals()
        self.save()

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

    def calculate_subtotal(self):
        """
        Get the total amount of the offer, which could be a set price or the products MSRP
        """
        return sum([item.total for item in self.order_items.all() ])

    def update_totals(self):
        """
        Sets the invoice total field by calculating its subtotal, any discounts, its shipping and tax.
        If by any reason the total is a negative value it will return 0 as vendor cannot credit any acount
        """
        self.subtotal = self.calculate_subtotal()
        discounts = self.get_discounts()
        self.calculate_shipping()
        self.calculate_tax()
        self.total = (self.subtotal - discounts) + self.tax + self.shipping
        if self.total < 0:
            self.total = 0

    def get_payment_billing_address(self):
        if not self.payments.first().billing_address:
            return ""
        return self.payments.first().billing_address.get_address_display()

    def get_absolute_management_url(self):
        """
        This is the url to the management's detail page for the Invoice
        """
        return reverse('vendor_admin:manager-order-detail', kwargs={'uuid': self.uuid})

    def get_recurring_order_items(self):
        """
        Gets the recurring order items in the invoice
        """
        return self.order_items.filter(offer__terms__lt=TermType.PERPETUAL)

    def get_recurring_total(self):
        """
        Gets the total price for all recurring order items in the invoice and subtracting any discounts.
        """
        recurring_time_order_items = self.get_recurring_order_items()
        return sum([ (order_item.total - order_item.discounts) for order_item in recurring_time_order_items.all()])

    def get_one_time_transaction_order_items(self):
        """
        Gets one time transation order items in the invoice
        """
        return self.order_items.filter(offer__terms__gte=TermType.PERPETUAL)

    def get_one_time_transaction_total(self):
        """
        Gets the total price for order items that will be purchased on a single transation. It also subtracts any discounts
        """
        one_time_order_items = self.get_one_time_transaction_order_items()
        return sum([ (order_item.total - order_item.discounts) for order_item in one_time_order_items.all()])

    def empty_cart(self):
        """
        Remove any offer/order_item if the invoice is in Cart State.
        """
        offers = []
        offers = list(itertools.chain.from_iterable([ [order_item.offer] * order_item.quantity for order_item in self.order_items.all()]))
        for offer in offers:
            self.remove_offer(offer)

    def get_next_billing_date(self):
        """
        Return the next billing date, if an invoice has two different billing dates it will return
        the upcoming one.
        """
        recurring_offers = self.order_items.filter(offer__terms__lt=TermType.PERPETUAL)

        if not recurring_offers.count():
            return None

        next_billing_dates = [order_item.offer.get_next_billing_date() for order_item in recurring_offers]

        next_billing_dates.sort()

        return next_billing_dates[0]

    def get_subscription_start_date(self):
        """
        Return the date the subscription will go into effect.
        """
        recurring_offers = self.order_items.filter(offer__terms__lt=TermType.PERPETUAL)

        if not recurring_offers.count():
            return None

        next_billing_dates = [get_subscription_start_date(order_item.offer, profile=self.profile) for order_item in recurring_offers]

        next_billing_dates.sort()

        return next_billing_dates[0]
    
    def get_billing_dates_and_prices(self):
        now = timezone.now()
        payments_info = {now: self.get_one_time_transaction_total()}
        
        for recurring_order_item in self.get_recurring_order_items():
            offer_total = (recurring_order_item.total - recurring_order_item.discounts)
            start_date = recurring_order_item.offer.get_term_start_date(now)
            subscription_start_date = get_subscription_start_date(recurring_order_item.offer, self.profile, start_date)

            if subscription_start_date in payments_info:
                payments_info.update({subscription_start_date: payments_info[subscription_start_date] + offer_total})
            else:
                payments_info[subscription_start_date] = offer_total

        sorted_payments = {key: payments_info[key] for key in sorted(payments_info.keys()) }
        
        return sorted_payments

    def get_next_billing_price(self):
        """
        Returns the price corresponding to the upcoming billing date.
        """
        recurring_offers = self.order_items.filter(offer__terms__lt=TermType.PERPETUAL)

        if not recurring_offers.count():
            return None

        if recurring_offers.count() == 1:
            return recurring_offers.first().total

        next_billing_date = recurring_offers.first().offer.get_next_billing_date()
        next_billing_date_price = recurring_offers.first().total

        for order_item in recurring_offers:
            if order_item.offer.get_next_billing_date() < next_billing_date:
                next_billing_date = order_item.offer.get_next_billing_date()
                next_billing_date_price = order_item.total

        return next_billing_date_price

    def get_savings(self):
        savings = 0

        savings = self.calculate_subtotal() - self.get_discounts()

        return savings

    def get_discounts(self):
        """
        Returns the sum of discounts and trial_discounts. Discounts are related to the offer.price and the offer.product.msrp,
        while trial discounts are related to the set offer.meta.trial_amount if it has a trial_occurrence.
        """
        if 'discounts' in self.vendor_notes:
            return self.vendor_notes['discounts']

        discounts = 0

        discounts = sum([order_item.discounts for order_item in self.order_items.all() if not self.profile.has_owned_product(order_item.offer.products.all())])

        trial_discounts = sum([order_item.price - order_item.trial_amount for order_item in self.order_items.all() if order_item.offer.has_trial_occurrences()])

        return discounts + trial_discounts

    def save_discounts_vendor_notes(self):
        """
        Once an invoice has been completed, this method saves the discounts applied to the invoice
        in the vendor_notes field. This makes it for faster lookup on get_discounts for future invoice
        views.
        """
        if not isinstance(self.vendor_notes, dict):
            self.vendor_notes = dict()

        self.vendor_notes["discounts"] = self.get_discounts()
        self.save()

    def save_promo_codes(self, codes):
        # TODO: Need to implement a consistant way on how to save promo codes in invoice.vendor_notes
        pass

    def get_promos(self):
        if 'promos' not in self.vendor_notes or not len(self.vendor_notes.get('promos', [])):
            return ""
        return self.vendor_notes['promos'].keys()


class OrderItem(CreateUpdateModelBase):
    '''
    A link for each item to a user after it's been purchased
    '''
    invoice = models.ForeignKey("vendor.Invoice", verbose_name=_("Invoice"), on_delete=models.CASCADE, related_name="order_items")
    offer = models.ForeignKey("vendor.Offer", verbose_name=_("Offer"), on_delete=models.CASCADE, related_name="order_items")
    quantity = models.IntegerField(_("Quantity"), default=1)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.offer} - {self.invoice.uuid}"

    @property
    def total(self):
        return self.quantity * self.price

    @property
    def price(self):
        """
        Price property is calculated if a offer.product has an MSRP different from zero.
        if product MSRP is zero it will return the corresponding offer.price.cost
        """
        if self.offer.get_msrp():
            return self.offer.get_msrp()
        return self.offer.current_price()

    @property
    def name(self):
        return self.offer.name

    @property
    def discounts(self):
        return self.offer.discount() * self.quantity

    @property
    def trial_amount(self):
        if self.receipts.count():
            if 'first' in self.receipts.first().meta:
                return self.offer.get_trial_amount()
        else:
            if self.offer.has_trial_occurrences():
                return self.offer.get_trial_amount()
        return self.offer.current_price()

    def get_total_display(self):
        if not self.total:
            return "0.00"

        return f'{self.total:2}'


##########
# Signals
##########
@receiver(user_logged_in)
def convert_session_cart_to_invoice(sender, request, **kwargs):
    if 'session_cart' in request.session:
        profile, created = request.user.customer_profile.get_or_create(site=get_site_from_request(request))
        cart = profile.get_cart()

        for offer_key in request.session['session_cart'].keys():
            cart.add_offer(Offer.objects.get(pk=offer_key), quantity=request.session['session_cart'][offer_key]['quantity'])

        del(request.session['session_cart'])
