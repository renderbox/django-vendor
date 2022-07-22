from django.contrib.sites.managers import CurrentSiteManager
from django.db import models

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




