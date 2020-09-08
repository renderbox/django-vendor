from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _

from .choice import CURRENCY_CHOICES

#########
# PRICE
#########

class Price(models.Model):
    offer = models.ForeignKey("vendor.Offer", on_delete=models.CASCADE, related_name="prices")
    cost = models.FloatField(blank=True, null=True)
    currency = models.CharField(_("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=settings.DEFAULT_CURRENCY)
    start_date = models.DateTimeField(_("Start Date"), help_text="When should the price first become available?")
    end_date = models.DateTimeField(_("End Date"), blank=True, null=True, help_text="When should the price expire?")
    priority = models.IntegerField(_("Priority"), help_text="Higher number takes priority", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.priority:       # TODO: Add check to see if this is the only price on the offer, then let it be 0.  If not, might need to do some assumptions to guess what it should be.
            self.priority = 0

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Price")
        verbose_name_plural = _("Prices")

    def __str__(self):
        return "{} for {}:{}".format(self.offer.name, dict(CURRENCY_CHOICES)[self.currency], self.cost)