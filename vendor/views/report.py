import csv

from django.http import StreamingHttpResponse
from django.utils.timezone import localtime
from django.contrib.sites.models import Site
# from django.shortcuts import render, redirect
# from django.contrib import messages
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.urls import reverse
# from django.conf import settings
# from django.utils.translation import ugettext as _
# from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import PermissionRequiredMixin

# from django.views.generic.edit import DeleteView
from django.views.generic.list import BaseListView
# from django.views.generic.detail import DetailView
# from django.views.generic import TemplateView

from vendor.models import Receipt, Invoice

# from vendor.models import Offer, Invoice, Payment, Address, CustomerProfile
# from vendor.models.choice import TermType
# from vendor.models.utils import set_default_site_id
# from vendor.processors import PaymentProcessor
# from vendor.forms import BillingAddressForm, CreditCardForm, AccountInformationForm

# # from vendor.models.address import Address as GoogleAddress

# # The Payment Processor configured in settings.py
# payment_processor = PaymentProcessor


# class CartView(LoginRequiredMixin, DetailView):
#     '''
#     View items in the cart
#     '''
#     model = Invoice

#     def get_object(self):
#         profile, created = self.request.user.customer_profile.get_or_create(
#             site=set_default_site_id())
#         return profile.get_cart()


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """
    
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


# class RecieptListCSV(PermissionRequiredMixin, BaseListView):
class CSVStreamRowView(BaseListView):
    """A base view for displaying a list of objects."""

    filename = "reciept_list.csv"
    # headers = 

    def get_queryset(self):
        return super().get_queryset()
    
    def get_row_data(self):
        rows = (["Row {}".format(idx), str(idx)] for idx in range(500))
        return rows

    def get(self, request, *args, **kwargs):
        rows = self.get_row_data()
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        #TODO: Figure out what to prepend the header without breaking the streaming generator
        response = StreamingHttpResponse((writer.writerow(row) for row in rows), content_type="text/csv")

        # Set the filename
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.filename)
        return response


class RecieptListCSV(CSVStreamRowView):
    filename = "reciepts.csv"
    model = Receipt

    def get_queryset(self):
        # TODO: Update to handle ranges from a POST
        return self.model.objects.filter(profile__site=Site.objects.get_current())      # Return reciepts only for profiles on this site

    def get_row_data(self):
        object_list = self.get_queryset()
        # header = ["RECIEPT_ID", "CREATED_TIME(ISO)", "USERNAME", "INVOICE_ID", "ORDER_ITEM", "OFFER_ID", "QUANTITY", "TRANSACTION_ID", "STATUS"]
        rows = [[str(obj.pk), obj.created.isoformat(), obj.profile.user.username, obj.order_item.invoice.pk, obj.order_item.offer, obj.order_item.pk, obj.order_item.quantity, obj.transaction, obj.get_status_display()] for obj in object_list]
        return rows

 
class InvoiceListCSV(CSVStreamRowView):
    filename = "invoices.csv"
    model = Invoice

    def get_queryset(self):
        # TODO: Update to handle ranges from a POST
        return self.model.on_site.all()
    
    def get_row_data(self):
        object_list = self.get_queryset()
        # header = ["INVOICE_ID", "CREATED_TIME(ISO)", "USERNAME", "CURRENCY", "TOTAL"]
        rows = ([str(obj.pk), obj.created.isoformat(), str(obj.profile.user.username), obj.currency, obj.total] for obj in object_list)
        return rows
