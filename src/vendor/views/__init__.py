from django.utils import timezone
from django.db.models import F
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist

from django.views import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.http import HttpResponse

from vendor.models import Offer, OrderItem, Invoice, Payment, Address
from vendor.models.address import Address as GoogleAddress
from vendor.models.choice import InvoiceStatus
from vendor.forms import BillingAddressForm, CreditCardForm

from .vendor_admin import AdminDashboardView, AdminInvoiceDetailView, AdminInvoiceListView
from .vendor import TransferExistingSubscriptionsToStripe

######################
# Order History Views
class OrderHistoryListView(LoginRequiredMixin, ListView):
    '''
    List of all the invoices generated by the current user on the current site.
    '''
    model = Invoice
    #TODO: filter to only include the current user's order history

    def get_queryset(self):
        try:
            return self.request.user.customer_profile.get().invoices.filter(status__gt=InvoiceStatus.CART)  # The profile and user are site specific so this should only return what's on the site for that user excluding the cart
        except ObjectDoesNotExist:         # Catch the actual error for the exception
            return []   # Return empty list if there is no customer_profile

class OrderHistoryDetailView(LoginRequiredMixin, DetailView):
    '''
    Details of an invoice generated by the current user on the current site.
    '''
    template_name = "vendor/invoice_history_detail.html"
    model = Invoice
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'