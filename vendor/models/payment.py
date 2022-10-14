import uuid

from django.db.models.aggregates import Sum
from django.db.models import Count
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from vendor.models.receipt import Receipt
from vendor.models.subscription import Subscription
from vendor.models.base import SoftDeleteModelBase
from vendor.models.choice import PurchaseStatus
from vendor.utils import get_display_decimal


class PaymentReportModelManager(models.Manager):
    def get_total_settled_purchases(self, start_date=None, end_date=None):
        qs = super().get_queryset()

        if not (start_date and end_date):
            return qs.filter(status=PurchaseStatus.SETTLED).aggregate(Sum('amount'))

        if start_date and end_date is None:
            return qs.filter(submitted_date__gte=start_date, status=PurchaseStatus.SETTLED).aggregate(Sum('amount'))

        if start_date is None and end_date:
            return qs.filter(submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).aggregate(Sum('amount'))

        return qs.filter(submitted_date__gte=start_date, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).aggregate((Sum('amount')))

    def get_total_settled_purchases_by_site(self, site, start_date=None, end_date=None):
        qs = super().get_queryset()

        if not (start_date and end_date):
            amount_qs = qs.filter(profile__site=site, status=PurchaseStatus.SETTLED).aggregate(Sum('amount'))

        elif start_date and end_date is None:
            amount_qs = qs.filter(profile__site=site, submitted_date__gte=start_date, status=PurchaseStatus.SETTLED).aggregate(Sum('amount'))

        elif start_date is None and end_date:
            amount_qs = qs.filter(profile__site=site, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).aggregate(Sum('amount'))

        else:
            amount_qs = qs.filter(profile__site=site, submitted_date__gte=start_date, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).aggregate(Sum('amount'))
        
        if not amount_qs['amount__sum']:
            return 0

        return amount_qs['amount__sum']

    
    def get_total_settled_purchases_by_subscription(self, site, start_date=None, end_date=None):
        qs = super().get_queryset()
        organized_data = {}

        if not (start_date and end_date):
            filtered_data = qs.filter(profile__site=site, status=PurchaseStatus.SETTLED).values('subscription').annotate(Sum('amount'))

        elif start_date and end_date is None:
            filtered_data = qs.filter(profile__site=site, submitted_date__gte=start_date, status=PurchaseStatus.SETTLED).values('subscription').annotate(Sum('amount'))

        elif start_date is None and end_date:
            filtered_data = qs.filter(profile__site=site, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('subscription').annotate(Sum('amount'))
        else:
            filtered_data = qs.filter(profile__site=site, submitted_date__gte=start_date, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('subscription').annotate((Sum('amount')))
        
        organized_data = {}
        for data in filtered_data:
            organized_data[Subscription.objects.get(pk=data['subscription']).name] = 0
        
        for data in filtered_data:
            organized_data[Subscription.objects.get(pk=data['subscription']).name] += data['amount__sum']

        return organized_data
    
    def get_total_settled_purchases_by_site_and_subscription(self, start_date=None, end_date=None):
        qs = super().get_queryset()
        organized_data = {}
        
        if not (start_date and end_date):
            filtered_data = qs.filter(status=PurchaseStatus.SETTLED).values('profile__site', 'subscription').annotate(Sum('amount'))

        elif start_date and end_date is None:
            filtered_data = qs.filter(submitted_date__gte=start_date, status=PurchaseStatus.SETTLED).values('profile__site', 'subscription').annotate(Sum('amount'))

        elif start_date is None and end_date:
            filtered_data = qs.filter(submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('profile__site', 'subscription').annotate(Sum('amount'))
        
        else:
            filtered_data = qs.filter(submitted_date__gte=start_date, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('profile__site', 'subscription').annotate((Sum('amount')))

        organized_data = {data['profile__site']: {} for data in filtered_data}
        
        for data in filtered_data:
            organized_data[data['profile__site']][Subscription.objects.get(pk=data['subscription']).name] = 0

        for data in filtered_data:
            organized_data[data['profile__site']][Subscription.objects.get(pk=data['subscription']).name] += data['amount__sum']

        return organized_data


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
    submitted_date = models.DateTimeField(_("Payment Date"), default=None, blank=True, null=True)
    transaction = models.CharField(_("Transaction ID"), max_length=80, blank=True, null=True)
    provider = models.CharField(_("Payment Provider"), max_length=30, blank=True, null=True)
    amount = models.FloatField(_("Amount"))
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), blank=True, on_delete=models.CASCADE, related_name="payments")
    billing_address = models.ForeignKey("vendor.Address", verbose_name=_("Billing Address"), on_delete=models.CASCADE, blank=True, null=True)
    result = models.JSONField(_("Result"), default=dict, blank=True, null=True)
    success = models.BooleanField(_("Successful"), default=False)
    payee_full_name = models.CharField(_("Name on Card"), max_length=50)
    payee_company = models.CharField(_("Company"), max_length=50, blank=True, null=True)
    status = models.IntegerField(_("Status"), choices=PurchaseStatus.choices, default=0)
    subscription = models.ForeignKey("vendor.Subscription", verbose_name=_("Subscription"), on_delete=models.CASCADE, related_name="payments", blank=True, null=True, default=None)

    reports = PaymentReportModelManager()

    def __str__(self):
        return f"{self.transaction} - {self.profile.user.username}"

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
