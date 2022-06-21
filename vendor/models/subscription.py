import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone, dateformat

from vendor.models.base import CreateUpdateModelBase, SoftDeleteModelBase
from vendor.models.choice import PurchaseStatus, SubscriptionStatus
from vendor.utils import get_payment_scheduled_end_date


class Subscription(SoftDeleteModelBase, CreateUpdateModelBase):
    '''
    A link for all the purchases a user has made. Contains subscription start and end date.
    This is generated for each item a user purchases so it can be checked in other code.
    '''
    uuid = models.UUIDField(_("UUID"), editable=False, unique=True, default=uuid.uuid4, null=False, blank=False)
    gateway_id = models.CharField(_("Subscription Gateway ID"), max_length=80)
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), on_delete=models.CASCADE, related_name="subscriptions")
    auto_renew = models.BooleanField(_("Auto Renew"), default=False)
    status = models.IntegerField(_("Status"), choices=SubscriptionStatus.choices, default=0)
    meta = models.JSONField(_("Meta"), default=dict, blank=True, null=True)

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def get_absolute_url(self):
        return reverse('vendor:customer-receipt', kwargs={'uuid': self.uuid})

    def void(self):
        """
        Funtion to void (not cancel) a receipt by making the end_date now and disabling
        access to the customer to that given product. If the receipt is related to a
        subscription to a Payment Gateway, make sure to also cancel such subscription
        in the given Payment Gateway.
        """
        receipt = self.receipts.order_by('created').last()
        receipt.end_date = timezone.now()
        receipt.meta['voided_on'] = receipt.end_date.strftime("%Y-%m-%d_%H:%M:%S")
        receipt.save()
        self.meta[receipt.end_date.strftime("%Y-%m-%d_%H:%M:%S")] = f'voided receipt: {receipt.uuid}'
        self.save()

    def cancel(self):
        self.status = SubscriptionStatus.CANCELED
        self.auto_renew = False
        self.meta[timezone.now().strftime("%Y-%m-%d_%H:%M:%S")] = 'Subscription Canceled'
        self.save()

    def is_on_trial(self):
        first_payment = Receipt.objects.filter(transaction=self.transaction, order_item__offer__site=self.order_item.offer.site).order_by('start_date').first()
        
        if self.end_date <= get_payment_scheduled_end_date(first_payment.order_item.offer, first_payment.start_date):
            return True
        return False
