import uuid

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.db import models
from django.db.models import Q, QuerySet, Count, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .base import CreateUpdateModelBase
from .choice import CURRENCY_CHOICES, TermType, PurchaseStatus, SubscriptionStatus
from .invoice import Invoice
from .utils import set_default_site_id
from vendor.config import DEFAULT_CURRENCY

from vendor.models.base import get_product_model
from vendor.models.choice import InvoiceStatus


#####################
# CUSTOMER PROFILE
#####################
class CustomerProfile(CreateUpdateModelBase):
    '''
    Additional customer information related to purchasing.
    This is what the Invoices are attached to.  This is abstracted from the user model directly do it can be mre flexible in the future.
    '''
    uuid = models.UUIDField(_("UUID"), editable=False, unique=True, default=uuid.uuid4, null=False, blank=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("User"), on_delete=models.CASCADE, related_name="customer_profile")
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=DEFAULT_CURRENCY)      # User's default currency
    site = models.ForeignKey(Site, verbose_name=_("Site"), on_delete=models.CASCADE, default=set_default_site_id, related_name="customer_profile")                      # For multi-site support
    meta = models.JSONField(_("Meta"), default=dict, blank=True, null=True)
        
    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"

    def __str__(self):
        if not self.user:
            return "New Customer Profile"
        return f"{self.user.username} - {self.site}"

    @property
    def email(self):
        return self.user.email

    def get_customer_profile_display(self):
        return str(self.user.username) + _("Customer Profile")

    def revert_invoice_to_cart(self):
        cart = self.invoices.get(status=InvoiceStatus.CHECKOUT)
        cart.status = InvoiceStatus.CART
        cart.save()

    def get_cart(self):
        if self.has_invoice_in_checkout():
            self.revert_invoice_to_cart()
    
        cart, created = self.invoices.get_or_create(status=InvoiceStatus.CART)
        return cart

    def get_checkout_cart(self):
        return self.invoices.filter(status=InvoiceStatus.CHECKOUT).first()

    def get_cart_or_checkout_cart(self):
        checkout_status = self.invoices.filter(status=InvoiceStatus.CHECKOUT, deleted=False).annotate(item_count=Count('order_items')).order_by('-item_count')
        cart_status = self.invoices.filter(status=InvoiceStatus.CART, deleted=False).annotate(item_count=Count('order_items')).order_by('-item_count')

        if checkout_status.count() > 1:  # There should only be one invoice in checkout status
            for invoice in checkout_status.all()[1:]:
                invoice.delete()
        
        if checkout_status:  # If there is an invoice in checkout status it there should be no invoices in cart status
            for invoice in cart_status.all():
                invoice.delete()

            return checkout_status.first()
        
        if not cart_status:  # There is no invoice in checkout or cart. Create a new one for user.
            cart, created = self.invoices.get_or_create(site=self.site, status=InvoiceStatus.CART)
            return cart

        if cart_status.count() > 1:  # There is more the one invoice in cart status. Remove all except one.
            for invoice in cart_status.all()[1:]:
                invoice.delete()

        return self.invoices.filter(status=InvoiceStatus.CART, deleted=False).first()

    def has_invoice_in_checkout(self):
        return bool(self.invoices.filter(status=InvoiceStatus.CHECKOUT).count())

    def filter_products(self, products):
        """
        returns the list of receipts that the user has a receipt for filtered by the products provided.
        """
        now = timezone.now()

        # Queryset or List of model records
        if isinstance(products, QuerySet) or isinstance(products, list):
            return self.receipts.filter(Q(products__in=products),
                                        Q(deleted=False),
                                        Q(start_date__lte=now) | Q(start_date=None),
                                        Q(end_date__gte=now) | Q(end_date=None))

        # Single model record
        return self.receipts.filter(Q(products=products),
                                    Q(deleted=False),
                                    Q(start_date__lte=now) | Q(start_date=None),
                                    Q(end_date__gte=now) | Q(end_date=None))

    def has_product(self, products):
        """
        returns true/false if the user has a receipt to a given product(s)
        it also checks against elegibility start/end/empty dates on consumable products and subscriptions
        """
        return bool(self.filter_products(products).count())

    def has_owned_product(self, products):
        # Queryset or List of model records
        if isinstance(products, QuerySet) or isinstance(products, list):
            return bool(self.receipts.filter(products__in=products).count())

        # Single model record
        return bool(self.receipts.filter(products=products).count())

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
        return bool(self.receipts.filter(products__in=products).first())

    def get_all_customer_products(self):
        Product = get_product_model()
        return Product.objects.filter(receipts__profile=self)

    def get_active_products(self):
         return set([receipt.products.first()  for receipt in self.get_active_receipts()])

    def get_active_offer_receipts(self, offer):
        return self.receipts.filter(Q(deleted=False), Q(order_item__offer=offer), Q(end_date__gte=timezone.now()) | Q(end_date=None))

    def get_active_receipts(self):
        return self.receipts.filter(Q(end_date__gte=timezone.now()) | Q(end_date=None))

    def get_inactive_receipts(self):
        return self.receipts.filter(end_date__lt=timezone.now())

    def get_active_product_and_offer(self):
        """
        Returns a tuple product and offer tuple that are related to the active receipt
        """
        return [(receipt.products.first(), receipt.order_item.offer) for receipt in self.receipts.filter(Q(deleted=False), Q(end_date__gte=timezone.now()) | Q(end_date=None))]

    def get_subscriptions(self):
        return self.subscriptions.all()

    def get_active_subscriptions(self):
        return self.subscriptions.filter(status=SubscriptionStatus.ACTIVE)

    def get_next_billing_date(self):
        next_billing_dates = []
        
        if not self.subscriptions.filter(status=SubscriptionStatus.ACTIVE).count():
            return None

        next_billing_dates = [subscription.get_next_billing_date() for subscription in self.get_active_subscriptions()]

        return sorted(next_billing_dates)[0]

    def get_last_payment_date(self):
        last_payment_dates = []
        
        if not self.subscriptions.count():
            return None

        last_payment_dates = [subscription.get_last_payment_date() for subscription in self.subscriptions.all()]

        return sorted(last_payment_dates)[-1]

    def get_payment_counts(self):
        return self.payments.filter(deleted=False, status=PurchaseStatus.SETTLED).count()

    def get_payment_sum(self):
        return self.payments.filter(deleted=False, status=PurchaseStatus.SETTLED).aggregate(Sum('amount'))

    def get_settled_payments(self):
        return self.payments.filter(deleted=False, status=PurchaseStatus.SETTLED).order_by('amount', 'submitted_date')

    def is_on_trial(self, offer):

        on_trial_receipt = next((receipt for receipt in self.get_active_offer_receipts(offer) if receipt.transaction and 'trial' in receipt.transaction), None)

        if on_trial_receipt:
            return True

        return False
