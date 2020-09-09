from calendar import monthrange
from datetime import datetime
from django import forms
from django.utils.translation import ugettext as _
from django.db.models import IntegerChoices
from .models import OrderItem, Address
from vendor.models.choice import PaymentTypes


# class AddToCartModelForm(forms.ModelForm):

#     class Meta:
#         model = OrderItem
#         fields = ['quantity']

# class AddToCartForm(forms.Form):
#     quantity = forms.IntegerField(required=True, initial=1)

# # class RequestRefundForm(forms.ModelForm):
# #     class Meta:
# #         model = Refund
# #         fields = ['reason']

class BillingAddressForm(forms.ModelForm):
    company = forms.CharField(label=_('Company'), required=False)

    field_order = ['name', 'company', 'country', 'address_1', 'address_2', 'locality', 'state', 'postal_code']
    class Meta:
        model = Address
        fields = ['name', 'company', 'address_1', 'address_2', 'locality', 'state', 'country', 'postal_code']


class CreditCardField(forms.CharField):

    # validates almost all of the example cards from PayPal
    # https://www.paypalobjects.com/en_US/vhelp/paypalmanager_help/credit_card_numbers.htm
    cards = [
        {
            'type': 'maestro',
            'patterns': [5018, 502, 503, 506, 56, 58, 639, 6220, 67],
            'length': [12, 13, 14, 15, 16, 17, 18, 19],
            'cvvLength': [3],
            'luhn': True
        }, {
            'type': 'forbrugsforeningen',
            'patterns': [600],
            'length': [16],
            'cvvLength': [3],
            'luhn': True
        }, {
            'type': 'dankort',
            'patterns': [5019],
            'length': [16],
            'cvvLength': [3],
            'luhn': True
        }, {
            'type': 'visa',
            'patterns': [4],
            'length': [13, 16],
            'cvvLength': [3],
            'luhn': True
        }, {
            'type': 'mastercard',
            'patterns': [51, 52, 53, 54, 55, 22, 23, 24, 25, 26, 27],
            'length': [16],
            'cvvLength': [3],
            'luhn': True
        }, {
            'type': 'amex',
            'patterns': [34, 37],
            'length': [15],
            'cvvLength': [3, 4],
            'luhn': True
        }, {
            'type': 'dinersclub',
            'patterns': [30, 36, 38, 39],
            'length': [14],
            'cvvLength': [3],
            'luhn': True
        }, {
            'type': 'discover',
            'patterns': [60, 64, 65, 622],
            'length': [16],
            'cvvLength': [3],
            'luhn': True
        }, {
            'type': 'unionpay',
            'patterns': [62, 88],
            'length': [16, 17, 18, 19],
            'cvvLength': [3],
            'luhn': False
        }, {
            'type': 'jcb',
            'patterns': [35],
            'length': [16],
            'cvvLength': [3],
            'luhn': True
        }
    ]

    def __init__(self, placeholder=None, *args, **kwargs):
        super(CreditCardField, self).__init__(
            # override default widget
            widget=forms.widgets.TextInput(attrs={'placeholder': placeholder, 'type':'tel'}), *args, **kwargs)

    default_error_messages = {
        'invalid': _(u'The credit card number is invalid'),
    }

    def clean(self, value):

        # ensure no spaces or dashes
        value = value.replace(' ', '').replace('-', '')

        # get the card type and its specs
        card = self.card_from_number(value)

        # if no card found, invalid
        if not card:
            raise forms.ValidationError(self.error_messages['invalid'])

        # check the length
        if not len(value) in card['length']:
            raise forms.ValidationError(self.error_messages['invalid'])

        # test luhn if necessary
        if card['luhn']:
            if not self.validate_mod10(value):
                raise forms.ValidationError(self.error_messages['invalid'])

        return value

    def card_from_number(self, num):
        # find this card, based on the card number, in the defined set of cards
        for card in self.cards:
            for pattern in card['patterns']:
                if (str(pattern) == str(num)[:len(str(pattern))]):
                    return card

    def validate_mod10(self, num):
        # validate card number using the Luhn (mod 10) algorithm
        checksum, factor = 0, 1
        for x in reversed(num):
            for y in str(factor * int(x)):
                checksum += int(y)
            factor -= 3
            factor = abs(factor)
        return checksum % 10 == 0


class PaymentFrom(forms.Form):
    payment_type = forms.ChoiceField(label=_("Payment Type"), choices=PaymentTypes.choices, widget=forms.widgets.HiddenInput)



class CreditCardForm(PaymentFrom):
    full_name = forms.CharField(required=True, label=_("Card Holder"), max_length=80)
    card_number = CreditCardField(placeholder=u'0000 0000 0000 0000', min_length=12, max_length=19)
    expire_month = forms.ChoiceField(required=True, choices=[(x, x) for x in range(1, 13)])
    expire_year = forms.ChoiceField(required=True, choices=[(x, x) for x in range(datetime.now().year, datetime.now().year + 15)])
    cvv_number = forms.IntegerField(required=True, label=_("CVV Number"), max_value=9999, widget=forms.TextInput(attrs={'size': '4'}))

    # def __init__(self, *args, **kwargs):
    #     self.payment_type = PaymentTypes.CREDIT_CARD
    #     self.payment_data = kwargs.pop('payment_data', None)
    #     super(CreditCardForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(CreditCardForm, self).clean()
        expire_month = cleaned_data.get('expire_month')
        expire_year = cleaned_data.get('expire_year')

        if not expire_year:
            self._errors["expire_year"] = self.error_class([_("You must select a valid Expiration year.")])
            del cleaned_data["expire_year"]
        if not expire_month:
            self._errors["expire_month"] = self.error_class([_("You must select a valid Expiration month.")])
            del cleaned_data["expire_month"]
        year = int(expire_year)
        month = int(expire_month)

        # find last day of the month
        day = monthrange(year, month)[1]
        expire = datetime(year, month, day)

        if datetime.now() > expire:
            self._errors["expire_year"] = self.error_class([_("The expiration date you entered is in the past.")])

        return cleaned_data
