from calendar import monthrange
from datetime import datetime
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib.sites.models import Site
from django.forms import inlineformset_factory
from django.forms.widgets import SelectDateWidget, TextInput
from django.utils.translation import gettext_lazy as _

from integrations.models import Credential

from vendor.config import VENDOR_PRODUCT_MODEL
from vendor.models import Address, Offer, Price, offer_term_details_default, CustomerProfile, Payment, Subscription
from vendor.models.choice import PaymentTypes, TermType, Country, USAStateChoices, SubscriptionStatus
from vendor.utils import get_site_from_request


Product = apps.get_model(VENDOR_PRODUCT_MODEL)

COUNTRY_CHOICE = getattr(settings, 'VENDOR_COUNTRY_CHOICE', Country)
COUNTRY_DEFAULT = getattr(settings, 'VENDOR_COUNTRY_DEFAULT', Country.US)


def get_available_country_choices():
    if isinstance(COUNTRY_CHOICE, list):
        return [(country.value, country.label) for country in Country if country.name in COUNTRY_CHOICE]
    return Country.choices


class PriceForm(forms.ModelForm):
    CHOICES = [('not_free', _('Purchase Price')),
               ('free', _('Free'))]
    price_select = forms.ChoiceField(label="", choices=CHOICES, widget=forms.widgets.RadioSelect())

    class Meta:
        model = Price
        fields = ['price_select', 'cost', 'currency',
                  'start_date', 'end_date', 'priority']

    def __init__(self, *args, **kwargs):
        super(PriceForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].widget.attrs['class'] = 'datepicker'
        self.fields['end_date'].widget.attrs['class'] = 'datepicker'
        self.fields['cost'].label = _('Price')
        self.fields['cost'].widget = TextInput()
        self.fields['cost'].widget.attrs['placeholder'] = '##.##'
        self.fields['cost'].widget.attrs['class'] = 'w-50'

        if self.instance.cost:
            self.initial['price_select'] = self.CHOICES[0]
        else:
            self.initial['price_select'] = self.CHOICES[1]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'site', 'available', 'description', 'meta']


class OfferForm(forms.ModelForm):
    products = forms.ModelMultipleChoiceField(label=_("Available Products:"), required=True, queryset=Product.objects.filter(site=settings.SITE_ID, available=True))

    class Meta:
        model = Offer
        fields = ['name', 'start_date', 'end_date', 'terms', 'term_details',
                  'term_start_date', 'available', 'offer_description', 'allow_multiple']

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        super(OfferForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].widget.attrs['class'] = 'datepicker'
        self.fields['end_date'].widget.attrs['class'] = 'datepicker'
        self.fields['term_start_date'].widget.attrs['class'] = 'datepicker'
        self.fields['available'].label = _('Available to Purchase')
        self.fields['products'].queryset = Product.objects.filter(site=get_site_from_request(request), available=True)

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data['name']:
            product_names = [product.name for product in self.cleaned_data['products']]
            if len(product_names) == 1:
                self.cleaned_data['name'] = product_names[0]
            else:
                self.cleaned_data['name'] = _("Bundle: ") + ", ".join(product_names)

        term_detail_defaults = [False for default in list(offer_term_details_default().keys()) if default not in cleaned_data['term_details']]

        if self.data['terms'] == str(TermType.SUBSCRIPTION) and False in term_detail_defaults:
            self.add_error('term_details', _("Invalid term details for subscription"))

        return cleaned_data


class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = ['name', 'first_name', 'last_name', 'country',
                  'address_1', 'address_2', 'locality', 'state', 'postal_code']

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)

        self.fields['name'].hidden = True
        self.fields['first_name'].widget.attrs.update({'placeholder': _('Enter First Name')})
        self.fields['last_name'].widget.attrs.update({'placeholder': _('Enter Last Name')})
        self.fields['country'].label = _("Billing Country/Region")

        self.fields['address_1'].widget.attrs.update({'placeholder': _('Enter Address')})
        self.fields['address_2'].widget.attrs.update({'placeholder': _('Enter Apt, Suite, Unit, Building, Floor, etc.')})
        self.fields['state'].widget.attrs.update({'placeholder': _('Enter State')})
        self.fields['locality'].widget.attrs.update({'placeholder': _('Enter City')})

        self.fields['postal_code'].required = True
        self.fields['postal_code'].label = _("Zip Code")
        self.fields['postal_code'].widget.attrs.update({'placeholder': _('Enter Zip')})
        self.fields['country'].choices = get_available_country_choices()
        
        if 'instance' in kwargs:
            self.initial['country'] = kwargs['instance'].country
        else:
            self.initial['country'] = Country[COUNTRY_DEFAULT].value


class AccountInformationForm(AddressForm):
    email = forms.EmailField(label=_('Email Address'), required=True)
    select_state = forms.ChoiceField(label=_("State"), choices=USAStateChoices.choices, required=False)
    prefix = "account_info"

    class Meta:
        model = Address
        fields = ['name', 'first_name', 'last_name', 'email', 'country',
                  'address_1', 'address_2', 'locality', 'state', 'postal_code']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'placeholder': _('Enter Email Address')})
        self.fields['select_state'].choices = [("", _("Select State"))] + self.fields['select_state'].choices

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get('state')
        select_state = cleaned_data.get('select_state')

        if not (state or select_state):
            self.add_error('select_state', _('This field is required.'))

        return cleaned_data


class BillingAddressForm(AddressForm):
    same_as_shipping = forms.BooleanField(label=_("Billing address is the same as shipping address"), required=False, initial=True)
    select_state = forms.ChoiceField(label=_("State"), choices=USAStateChoices.choices, required=False)
    prefix = "billing"

    class Meta:
        model = Address
        fields = ['same_as_shipping', 'name', 'first_name', 'last_name',
                  'country', 'address_1', 'address_2', 'locality', 'state', 'postal_code']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['select_state'].choices = [("", _("Select State"))] + self.fields['select_state'].choices

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get('state')
        select_state = cleaned_data.get('select_state')

        if not (state or select_state):
            self.add_error('select_state', _('This field is required.'))

        return cleaned_data


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
        super(CreditCardField, self).__init__(widget=forms.widgets.TextInput(attrs={'placeholder': placeholder, 'type': 'tel'}), *args, **kwargs)

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
    full_name = forms.CharField(required=True, label=_("Name on Card"), max_length=80)
    card_number = CreditCardField(label=_("Credit Card Number"), placeholder=u'0000 0000 0000 0000', min_length=12, max_length=19)
    expire_month = forms.ChoiceField(required=True, label=_("Expiration Month"), choices=[(x, f'{x:02d}') for x in range(1, 13)])
    expire_year = forms.ChoiceField(required=True, label=_("Expiration Year"))
    cvv_number = forms.CharField(required=True, label=_("CVV Number"), max_length=4, min_length=3, widget=forms.TextInput(attrs={'size': '4', 'placeholder': _('Enter CVV')}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = datetime.now()
        self.fields['expire_year'].choices = [(x, x) for x in range(today.year, today.year + 15)]
        self.fields['expire_year'].initial = (today.year, today.year)
        self.fields['full_name'].widget.attrs.update({'placeholder': _('Enter Name on Card')})

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
            raise forms.ValidationError(_("You must select a valid expiration month"), code='required')

        return expire_month

    def clean_expire_year(self):
        expire_year = self.cleaned_data.get('expire_year')

        if not expire_year:
            raise forms.ValidationError(_("You must select a valid expiration year"), code='required')

        return expire_year

    def clean_cvv_number(self):
        cvv_number = self.cleaned_data.get('cvv_number')

        if not cvv_number.isdigit():
            raise forms.ValidationError(_("CVV must be all digits"))

        return cvv_number

    def expiration_date_valid(self, expire_month, expire_year):
        year = int(expire_year)
        month = int(expire_month)

        # find last day of the month
        day = monthrange(year, month)[1]
        expire = datetime(year, month, day)

        if datetime.now() > expire:
            self._errors["expire_year"] = self.error_class([_("The expiration date you entered is in the past.")])
            self._errors["expire_month"] = self.error_class([_("Check expiration")])
            return False
        return True


class DateRangeForm(forms.Form):
    start_date = forms.DateField(required=False, label=_("Start Date"), widget=SelectDateWidget())
    end_date = forms.DateField(required=False, label=_("End Date"), widget=SelectDateWidget())

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if end_date and end_date < start_date:
            self.add_error('end_date', _('End Date cannot be before Start Date'))
            del(cleaned_data['end_date'])

        return cleaned_data


class DateTimeRangeForm(forms.Form):
    start_date = forms.DateTimeField(required=False, label=_("Start Date"), widget=SelectDateWidget())
    end_date = forms.DateTimeField(required=False, label=_("End Date"), widget=SelectDateWidget())

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if end_date and end_date < start_date:
            self.add_error('end_date', _('End Date cannot be before Start Date'))
            del(cleaned_data['end_date'])

        return cleaned_data


class SiteSelectForm(forms.Form):
    site = forms.ModelChoiceField(queryset=Site.objects.all())

class OfferSiteSelectForm(SiteSelectForm):
    offer = forms.ModelChoiceField(queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'site' in self.initial or 'site' in self.data:
            site = self.initial.get('site', self.data['site'])
            self.fields['offer'].queryset = Offer.objects.filter(site=site)
        else:
            self.fields['offer'].widget = forms.HiddenInput()


class SubscriptionForm(forms.Form):
    site = forms.ModelChoiceField(queryset=Site.objects.all())
    profile = forms.ModelChoiceField(queryset=None)
    subscription_id = forms.CharField(max_length=80)
    status = forms.ChoiceField(choices=SubscriptionStatus.choices)
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not ('site' in self.initial or 'site' in self.data):
            raise KeyError("site needs to be inluded in either initial or data attributes")

        site = self.initial.get('site', self.data.get('site'))
            
        self.fields['site'].widget = forms.HiddenInput()
        self.fields['profile'].queryset = CustomerProfile.objects.filter(site=site).order_by('user__username').select_related('user')


class SubscriptionAddPaymentForm(forms.ModelForm):
    offer = forms.ModelChoiceField(queryset=None)
    
    class Meta:
        model = Payment
        fields = ['subscription', 'profile', 'submitted_date', 'transaction', 'amount', 'success', 'status', 'payee_full_name']

    def __init__(self, *args, **kwargs):
        offers_queryset = None
        if 'site' in kwargs:
            offers_queryset = Offer.objects.filter(site=kwargs.get('site'))
            del(kwargs['site'])

        super().__init__(*args, **kwargs)

        self.fields['offer'].widget = forms.HiddenInput()
        self.fields['offer'].queryset = offers_queryset
        self.fields['submitted_date'].widget.attrs['class'] = 'datepicker'
        self.fields['subscription'].widget = forms.HiddenInput()
        self.fields['profile'].widget = forms.HiddenInput()

##########
# From Sets
##########


PriceFormSet = inlineformset_factory(
    Offer,
    Price,
    form=PriceForm,
    can_delete=False,
    exclude=('offer',),
    validate_max=True,
    min_num=1,
    extra=0)


class AuthorizeNetIntegrationForm(forms.ModelForm):

    class Meta:
        model = Credential
        fields = ['client_id', 'public_key', 'private_key']
        labels = {
            'client_id': _("API ID"),
            'public_key': _("Transaction Key"),
            'private_key': _("Signature ID")
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client_id'].required = True
        self.fields['public_key'].required = True
        self.fields['private_key'].required = True


class StripeIntegrationForm(forms.ModelForm):

    class Meta:
        model = Credential
        fields = ['public_key', 'private_key']
        labels = {
            'public_key': _("Publishable Client Key"),
            'private_key': _("Secret Server Key")
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['public_key'].required = True
        self.fields['private_key'].required = True