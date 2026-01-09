from django.db import models
from django.utils.translation import gettext_lazy as _
from iso4217 import Currency

from vendor.config import DEFAULT_CURRENCY

from .choice import CURRENCY_CHOICES
from .utils import get_conversion_factor


#########
# PRICE
#########
class Price(models.Model):
    offer = models.ForeignKey(
        "vendor.Offer",
        verbose_name=_("Offer"),
        on_delete=models.CASCADE,
        related_name="prices",
    )
    # TODO: Change to an integer field and store in cents to avoid floating point issues.  Create necessary
    #       migrations and update all code that interacts with this field to convert to/from cents.
    cost = models.IntegerField(_("Cost"), blank=True, null=True)
    currency = models.CharField(
        _("Currency"), max_length=4, choices=CURRENCY_CHOICES, default=DEFAULT_CURRENCY
    )
    start_date = models.DateTimeField(
        _("Start Date"), help_text=_("When should the price first become available?")
    )
    end_date = models.DateTimeField(
        _("End Date"),
        blank=True,
        null=True,
        help_text=_("When should the price expire?"),
    )
    priority = models.IntegerField(
        _("Priority"),
        help_text=_("Higher number takes priority"),
        blank=True,
        null=True,
        default=0,
    )

    # Convert the price into the appropriate display format based on the currency. For example, if the currency is USD, divide by 100 to convert from cents to dollars. # noqa: E501
    def display_cost(self):
        if self.cost is None:
            return None
        conversion_factor = get_conversion_factor(self.currency)
        decimals = 0 if conversion_factor == 1 else len(str(int(conversion_factor))) - 1
        amount = self.cost / conversion_factor
        try:
            symbol = Currency(self.currency.upper()).symbol or self.currency.upper()
        except (KeyError, ValueError, AttributeError):
            symbol = self.currency.upper()
        return "{}{:.{}f}".format(symbol, amount, decimals)

    def save(self, *args, **kwargs):
        if not self.priority:
            # TODO: Add check to see if this is the only price on the offer, then let it be 0.
            # If not, might need to do some assumptions to guess what it should be.
            self.priority = 0

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Price"
        verbose_name_plural = "Prices"

    def __str__(self):
        return "{} for {} ({}) -> ({})".format(
            self.offer.name,
            self.display_cost(),
            dict(CURRENCY_CHOICES)[self.currency],
            self.cost,
        )
