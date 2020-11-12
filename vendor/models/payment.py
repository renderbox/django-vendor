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
    invoice = models.ForeignKey("vendor.Invoice", verbose_name="Invoice", on_delete=models.CASCADE, related_name="payments")
    created = models.DateTimeField("Date Created", auto_now_add=True)
    transaction = models.CharField("Transaction ID", max_length=50)
    provider = models.CharField("Payment Provider", max_length=30)
    amount = models.FloatField("Amount")
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name="Purchase Profile", blank=True, null=True, on_delete=models.SET_NULL, related_name="payments")
    billing_address = models.ForeignKey("vendor.Address", verbose_name="Billing Address", on_delete=models.CASCADE, blank=True, null=True)
    result = models.JSONField("Result", default=dict, blank=True, null=True)
    success = models.BooleanField("Successful", default=False)
    payee_full_name = models.CharField("Name on Card", max_length=50)
    payee_company = models.CharField("Company", max_length=50, blank=True, null=True)
    

# class Coupon(models.Model):
#     pass


# class GiftCode(models.Model):
#     pass
