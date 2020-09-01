from django.db.models import IntegerChoices
from django.utils.translation import ugettext as _

class PaymentTypes(IntegerChoices):
    CREDIT_CARD = 10, _('Credit Card')
    BANK_ACCOUNT = 20, _('Bank Account')
    PAY_PAL = 30, _('Pay Pal')
    MOBILE = 40, _('Mobile')


class TransactionTypes(IntegerChoices):
    AUTHORIZE = 10
    CAPTURE = 20
    SETTLE = 30
    VOID = 40
    REFUND = 50