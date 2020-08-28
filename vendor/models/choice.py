from django.utils.translation import gettext_lazy as _

from iso4217 import Currency

###########
# CHOICES
###########

CURRENCY_CHOICES = [(c.name, c.value) for c in Currency ]

class PurchaseStatus(models.IntegerChoice):
    QUEUED = 1, _("Queued")
    ACTIVE = 2, _("Active")
    AUTHORIZED = 10, _("Authorized")
    CAPTURED = 15, _("Captured")
    COMPLETE = 20, _("Completed")
    CANCELED = 30, _("Canceled")
    REFUNDED = 35, _("Refunded")
