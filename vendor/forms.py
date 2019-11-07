from django.forms import ModelForm
from django import forms
# from django.utils.translation import ugettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import OrderItem


class AddToCartForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['offer',]