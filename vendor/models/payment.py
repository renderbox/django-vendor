import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _

##########
# PAYMENT
##########

class Payment(models.Model):
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
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), blank=True, null=True, on_delete=models.SET_NULL, related_name="payments")
    billing_address = models.ForeignKey("vendor.Address", verbose_name=_("Billing Address"), on_delete=models.CASCADE, blank=True, null=True)
    result = models.JSONField(_("Result"), default=dict, blank=True, null=True)
    success = models.BooleanField(_("Successful"), default=False)
    payee_full_name = models.CharField(_("Name on Card"), max_length=50)
    payee_company = models.CharField(_("Company"), max_length=50, blank=True, null=True)
    

# class Coupon(models.Model):
#     pass


# class GiftCode(models.Model):
#     pass
