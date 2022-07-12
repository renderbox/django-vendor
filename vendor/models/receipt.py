import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone, dateformat

from vendor.models.base import CreateUpdateModelBase, SoftDeleteModelBase
from vendor.models.choice import PurchaseStatus
from vendor.utils import get_payment_scheduled_end_date


class Receipt(SoftDeleteModelBase, CreateUpdateModelBase):
    '''
    A link for all the purchases a user has made. Contains subscription start and end date.
    This is generated for each item a user purchases so it can be checked in other code.
    '''
    uuid = models.UUIDField(_("UUID"), editable=False, unique=True, default=uuid.uuid4, null=False, blank=False)
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), on_delete=models.CASCADE, related_name="receipts")
    order_item = models.ForeignKey('vendor.OrderItem', verbose_name=_("Order Item"), on_delete=models.CASCADE, related_name="receipts")
    start_date = models.DateTimeField(_("Start Date"), blank=True, null=True)
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True)
    vendor_notes = models.JSONField(_("Vendor Notes"), default=dict, blank=True, null=True)
    transaction = models.CharField(_("Transaction"), max_length=80, blank=True, null=True)
    subscription = models.ForeignKey("vendor.Subscription", verbose_name=_("Subscription"), on_delete=models.CASCADE, related_name="receipts", blank=True, null=True, default=None)
    meta = models.JSONField(_("Meta"), default=dict, blank=True, null=True)

    class Meta:
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"

    def __str__(self):
        return f"{self.profile.user.username} - {self.order_item.offer.name}"

    def get_absolute_url(self):
        return reverse('vendor:customer-receipt', kwargs={'uuid': self.uuid})

    def is_on_trial(self):
        first_payment = Receipt.objects.filter(transaction=self.transaction, order_item__offer__site=self.order_item.offer.site).order_by('start_date').first()
        
        if self.end_date <= get_payment_scheduled_end_date(first_payment.order_item.offer, first_payment.start_date):
            return True
        return False
