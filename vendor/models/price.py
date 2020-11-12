from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .choice import CURRENCY_CHOICES
from vendor.config import DEFAULT_CURRENCY

#########
# PRICE
#########

class Price(models.Model):
    offer = models.ForeignKey("vendor.Offer", verbose_name="Offer", on_delete=models.CASCADE, related_name="prices")
    cost = models.FloatField("Cost", blank=True, null=True)
    currency = models.CharField("Currency", max_length=4, choices=CURRENCY_CHOICES, default=DEFAULT_CURRENCY)
    start_date = models.DateTimeField("Start Date", help_text="When should the price first become available?")
    end_date = models.DateTimeField("End Date", blank=True, null=True, help_text="When should the price expire?")
    priority = models.IntegerField("Priority", help_text="Higher number takes priority", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.priority:       # TODO: Add check to see if this is the only price on the offer, then let it be 0.  If not, might need to do some assumptions to guess what it should be.
            self.priority = 0

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Price"
        verbose_name_plural = "Prices"

    def __str__(self):
        return "{} for {}:{}".format(self.offer.name, dict(CURRENCY_CHOICES)[self.currency], self.cost)
