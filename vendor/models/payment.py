import uuid

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from vendor.models.receipt import Receipt
from vendor.models.base import SoftDeleteModelBase
from vendor.utils import get_display_decimal


##########
# PAYMENT
##########
class Payment(SoftDeleteModelBase):
    '''
    Payments
    - Payments are typically from a Credit Card, PayPal or ACH
    - Multiple Payments can be applied to an invoice
    - Gift cards can be used as payments
    - Discounts are Payment credits
    '''
    uuid = models.UUIDField(_("UUID"), editable=False, unique=True, default=uuid.uuid4, null=False, blank=False)
    invoice = models.ForeignKey("vendor.Invoice", verbose_name=_("Invoice"), on_delete=models.CASCADE, related_name="payments")
    created = models.DateTimeField(_("Date Created"), auto_now_add=True)
    transaction = models.CharField(_("Transaction ID"), max_length=50)
    provider = models.CharField(_("Payment Provider"), max_length=30)
    amount = models.FloatField(_("Amount"))
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), blank=True, on_delete=models.CASCADE, related_name="payments")
    billing_address = models.ForeignKey("vendor.Address", verbose_name=_("Billing Address"), on_delete=models.CASCADE, blank=True, null=True)
    result = models.JSONField(_("Result"), default=dict, blank=True, null=True)
    success = models.BooleanField(_("Successful"), default=False)
    payee_full_name = models.CharField(_("Name on Card"), max_length=50)
    payee_company = models.CharField(_("Company"), max_length=50, blank=True, null=True)

    def get_related_receipts(self):
        return Receipt.objects.filter(transaction=self.transaction)

    def get_receipt(self):
        try:
            return Receipt.objects.get(transaction=self.transaction, created__year=self.created.year, created__month=self.created.month, created__day=self.created.day)
        except ObjectDoesNotExist:
            return None
        except MultipleObjectsReturned:
            return Receipt.objects.filter(transaction=self.transaction, created__year=self.created.year, created__month=self.created.month, created__day=self.created.day).first()

    def get_amount_display(self):
        return get_display_decimal(self.amount)
