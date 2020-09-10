from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _

from .base import CreateUpdateModelBase
from vendor.models.choice import PurchaseStatus

#####################
# TAX CLASSIFIER
#####################

class Receipt(CreateUpdateModelBase):
    '''
    A link for all the purchases a user has made. Contains subscription start and end date.
    This is generated for each item a user purchases so it can be checked in other code.
    '''
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), null=True, on_delete=models.CASCADE, related_name="receipts")
    order_item = models.ForeignKey('vendor.OrderItem', verbose_name=_("Order Item"), on_delete=models.CASCADE, related_name="receipts")
    product = models.ForeignKey(settings.VENDOR_PRODUCT_MODEL, on_delete=models.CASCADE, related_name="receipts", blank=True, null=True)           # TODO:  Goal is to make it easier to check to see if a user owns the product. WHAT IF IT IS A BUNDLE
    start_date = models.DateTimeField(_("Start Date"), blank=True, null=True)
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True)
    auto_renew = models.BooleanField(_("Auto Renew"), default=False)        # For subscriptions
    vendor_notes = models.JSONField(_("Vendor Notes"), default=dict)
    transaction = models.CharField(_("Transaction"), max_length=80)
    status = models.IntegerField(_("Status"), choices=PurchaseStatus.choices, default=0)       # Fulfilled, Refund
    meta = models.JSONField(default=dict)
    class Meta:
        verbose_name = _("Receipt")
        verbose_name_plural = _("Receipts")

    def __str__(self):
        return "%s - %s - %s" % (self.profile.user.username, self.order_item.offer.name, self.created.strftime('%Y-%m-%d %H:%M'))
