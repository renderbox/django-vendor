from django.forms import ModelForm
from django import forms
# from django.utils.translation import ugettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import OrderItem


class AddToCartModelForm(forms.ModelForm):

    class Meta:
        model = OrderItem
        fields = ['quantity']

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(required=True, initial=1)


class PaymentForm(forms.Form):
    stripeToken = forms.CharField(required=False)


class RequestRefundForm(forms.Form):
    pass


# class RequestRefundForm(forms.ModelForm):
#     class Meta:
#         model = Refund
#         fields = ['reason']
    