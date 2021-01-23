import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.utils import timezone, dateformat

from .base import CreateUpdateModelBase

from vendor.config import VENDOR_PRODUCT_MODEL
from vendor.models.choice import PurchaseStatus


class Receipt(CreateUpdateModelBase):
    '''
    A link for all the purchases a user has made. Contains subscription start and end date.
    This is generated for each item a user purchases so it can be checked in other code.
    '''
    uuid = models.UUIDField(_("UUID"), editable=False, unique=True, default=uuid.uuid4, null=False, blank=False)
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), null=True, on_delete=models.CASCADE, related_name="receipts")
    order_item = models.ForeignKey('vendor.OrderItem', verbose_name=_("Order Item"), on_delete=models.CASCADE, related_name="receipts")
    start_date = models.DateTimeField(_("Start Date"), blank=True, null=True)
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True)
    auto_renew = models.BooleanField(_("Auto Renew"), default=False)        # For subscriptions
    vendor_notes = models.JSONField(_("Vendor Notes"), default=dict)
    transaction = models.CharField(_("Transaction"), max_length=80)
    status = models.IntegerField(_("Status"), choices=PurchaseStatus.choices, default=0)       # Fulfilled, Refund
    meta = models.JSONField(_("Meta"), default=dict)
    # TODO: Add final purchase price to the receipt for tracking.
    # TODO: Add Site field for easier tracking?
    # the product connection comes from the ProductModelBase to not trigger a migration on subclassing PMB

    class Meta:
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"

    def __str__(self):
        return "%s - %s - %s" % (self.profile.user.username, self.order_item.offer.name, self.created.strftime('%Y-%m-%d %H:%M'))

    def get_absolute_url(self):
        return reverse('vendor:customer-receipt', kwargs={'uuid': self.uuid})

    def void(self):
        """
        Funtion to void (not cancel) a receipt by making the end_date now and disabling 
        access to the customer to that given product. If the receipt is related to a
        subscription to a Payment Gateway, make sure to also cancel such subscription
        in the given Payment Gateway. 
        """
        self.end_date = timezone.now()
        self.meta['voided_on'] = dateformat.format(self.end_date, 'Y-M-d H:i:s')


