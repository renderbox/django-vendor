from calendar import monthrange
from datetime import datetime
from django import forms
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import IntegerChoices
from django.forms import inlineformset_factory
from django.forms.widgets import SelectDateWidget
from django.utils.translation import ugettext as _

from .config import VENDOR_PRODUCT_MODEL
from .models import Address, Offer, OrderItem, Price
from .models.choice import PaymentTypes, TermType

Product = apps.get_model(VENDOR_PRODUCT_MODEL)
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

        
class PriceForm(forms.ModelForm):
    start_date = forms.DateField(widget=SelectDateWidget())
    end_date = forms.DateField(widget=SelectDateWidget())
    class Meta:
        model = Price
        fields = ['cost', 'currency', 'start_date', 'end_date', 'priority']


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = ['sku', 'name', 'site', 'available', 'description', 'meta']


class OfferForm(forms.ModelForm):
    # TODO: How to fileter per site?
    products = forms.ModelMultipleChoiceField(label=_("Available Products:"), required=True, queryset=Product.objects.filter(available=True))
    start_date = forms.DateField(widget=SelectDateWidget())
    end_date = forms.DateField(widget=SelectDateWidget())
    term_start_date = forms.DateField(widget=SelectDateWidget())

    class Meta:
        model = Offer
        fields = ['name', 'start_date', 'end_date', 'terms', 'term_details', 'term_start_date', 'available', 'offer_description']

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data['name']:
            product_names = [ product.name for product in self.cleaned_data['products'] ]
            if len(product_names) == 1:
                self.cleaned_data['name'] = product_names[0]
            else:
                self.cleaned_data['name'] = "Bundle: " + ", ".join(product_names)

        if self.data['terms'] == TermType.SUBSCRIPTION and not cleaned_data['term_details']:
            self.add_error('term_details', _("Invalid term details for subscription"))

        return cleaned_data


PriceFormSet = inlineformset_factory(
    Offer,
    Price,
    form=PriceForm,
    can_delete=True,
    exclude=('offer',),
    validate_max=True,
    min_num=1,
    extra=0)


class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = ['name',  'first_name', 'last_name', 'country', 'address_1', 'address_2', 'locality', 'state', 'postal_code']


class AccountInformationForm(AddressForm):
    email = forms.EmailField(label=_('email'), required=True)

    class Meta:
        model = Address
        fields = ['name',  'first_name', 'last_name', 'email', 'country', 'address_1', 'address_2', 'locality', 'state', 'postal_code']

class BillingAddressForm(AddressForm):
    same_as_shipping = forms.BooleanField(label=_("Billing Address is the same as Shipping Address"), required=False)
    company = forms.CharField(label=_('Company'), required=False)

    class Meta:
        model = Address
        fields = ['same_as_shipping', 'name', 'company', 'first_name', 'last_name', 'country', 'address_1', 'address_2', 'locality', 'state', 'postal_code']

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
    full_name = forms.CharField(required=True, label=_("Card Holder Name"), max_length=80)
    card_number = CreditCardField(placeholder=u'0000 0000 0000 0000', min_length=12, max_length=19)
    expire_month = forms.ChoiceField(required=True, choices=[(x, x) for x in range(1, 13)])
    expire_year = forms.ChoiceField(required=True, choices=[(x, x) for x in range(datetime.now().year, datetime.now().year + 15)])
    cvv_number = forms.IntegerField(required=True, label=_("CVV Number"), max_value=9999, widget=forms.TextInput(attrs={'size': '4'}))

    def clean(self):
        cleaned_data = super(CreditCardForm, self).clean()
        expire_month = cleaned_data.get('expire_month')
        expire_year = cleaned_data.get('expire_year')

        if not self.expiration_date_valid(expire_month, expire_year):
            del(cleaned_data['expire_month'])
            del(cleaned_data['expire_year'])

        
        return cleaned_data

    def clean_expire_month(self):
        expire_month = self.cleaned_data.get('expire_month')

        if not expire_month:
            raise forms.ValidationError(_("You must select a valid expiration month"))

        return expire_month

    def clean_expire_year(self):
        expire_year = self.cleaned_data.get('expire_year')

        if not expire_year:
            raise forms.ValidationError(_("You must select a valid expiration year"))

        return expire_year

    def expiration_date_valid(self, expire_month, expire_year):
        year = int(expire_year)
        month = int(expire_month)

        # find last day of the month
        day = monthrange(year, month)[1]
        expire = datetime(year, month, day)

        if datetime.now() > expire:
            self._errors["expire_year"] = self.error_class([_("The expiration date you entered is in the past.")])
            self._errors["expire_month"] = self.error_class([_("")])
            return False
        return True