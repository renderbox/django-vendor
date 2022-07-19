from django.db.models.aggregates import Sum
from django.db.models import Count
from django.contrib.sites.managers import CurrentSiteManager
from django.db import models

from vendor.models.choice import PurchaseStatus, SubscriptionStatus

class ActiveManager(models.Manager):
    """
    This Model Manger returns offers that are available
    """
    def get_queryset(self):
        return super().get_queryset().filter(available=True)


class ActiveCurrentSiteManager(CurrentSiteManager):
    """
    This Model Manager return offers per site that are available
    """
    def get_queryset(self):
        return super().get_queryset().filter(available=True)


class SoftDeleteManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)


class CurrentSiteSoftDeleteManager(CurrentSiteManager):

    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)


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

    def get_total_settled_purchases_by_site(self, start_date=None, end_date=None):
        qs = super().get_queryset()

        if not (start_date and end_date):
            return qs.filter(status=PurchaseStatus.SETTLED).values('profile__site').annotate(Sum('amount'))

        if start_date and end_date is None:
            return qs.filter(submitted_date__gte=start_date, status=PurchaseStatus.SETTLED).values('profile__site').annotate(Sum('amount'))

        if start_date is None and end_date:
            return qs.filter(submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('profile__site').annotate(Sum('amount'))

        return qs.filter(submitted_date__gte=start_date, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('profile__site').annotate((Sum('amount')))

    
    def get_total_settled_purchases_by_subscription(self, start_date=None, end_date=None):
        qs = super().get_queryset()

        if not (start_date and end_date):
            return qs.filter(status=PurchaseStatus.SETTLED).values('subscription').annotate(Sum('amount'))

        elif start_date and end_date is None:
            return qs.filter(submitted_date__gte=start_date, status=PurchaseStatus.SETTLED).values('subscription').annotate(Sum('amount'))

        elif start_date is None and end_date:
            return qs.filter(submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('subscription').annotate(Sum('amount'))

        return qs.filter(submitted_date__gte=start_date, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('subscription').annotate((Sum('amount')))
    
    def get_total_settled_purchases_by_site_and_subscription(self, start_date=None, end_date=None):
        qs = super().get_queryset()

        if not (start_date and end_date):
            return qs.filter(status=PurchaseStatus.SETTLED).values('profile__site', 'subscription').annotate(Sum('amount'))

        elif start_date and end_date is None:
            return qs.filter(submitted_date__gte=start_date, status=PurchaseStatus.SETTLED).values('profile__site', 'subscription').annotate(Sum('amount'))

        elif start_date is None and end_date:
            return qs.filter(submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('profile__site', 'subscription').annotate(Sum('amount'))

        return qs.filter(submitted_date__gte=start_date, submitted_date__lte=end_date, status=PurchaseStatus.SETTLED).values('profile__site', 'subscription').annotate((Sum('amount')))


class SubscriptionReportModelManger(models.Manager):
    def get_total_cancelled_subscriptions(self, start_date=None, end_date=None):
        qs = super().get_queryset()
        
        if not (start_date and end_date):
            return qs.filter(status=SubscriptionStatus.CANCELED)

        elif start_date and end_date is None:
            return qs.filter(status=SubscriptionStatus.CANCELED, updated__date__gte=start_date)

        elif start_date is None and end_date:
            return qs.filter(status=SubscriptionStatus.CANCELED, updated__date__lte=end_date)
            
        return qs.filter(status=SubscriptionStatus.CANCELED, updated__date__gte=start_date, updated__date__lte=end_date)
