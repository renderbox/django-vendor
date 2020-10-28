import csv

from django.http import StreamingHttpResponse
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
class RecieptListCSV(BaseListView):
    """A base view for displaying a list of objects."""

    def get_queryset(self):
        return super().get_queryset()
    
    def get(self, request, *args, **kwargs):
        # self.object_list = self.get_queryset()
        # allow_empty = self.get_allow_empty()

        # if not allow_empty:
        #     # When pagination is enabled and object_list is a queryset,
        #     # it's better to do a cheap query than to load the unpaginated
        #     # queryset in memory.
        #     if self.get_paginate_by(self.object_list) is not None and hasattr(self.object_list, 'exists'):
        #         is_empty = not self.object_list.exists()
        #     else:
        #         is_empty = not self.object_list
        #     if is_empty:
        #         raise Http404(_('Empty list and “%(class_name)s.allow_empty” is False.') % {
        #             'class_name': self.__class__.__name__,
        #         })
        # context = self.get_context_data()
        # return self.render_to_response(context)
        rows = (["Row {}".format(idx), str(idx)] for idx in range(500))
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse((writer.writerow(row) for row in rows), content_type="text/csv")
        # Set the filename
        response['Content-Disposition'] = 'attachment; filename="reciepts.csv"'
        return response


# class InvoiceListCSV(PermissionRequiredMixin, BaseListView):
#     def get(self, request, *args, **kwargs):
#         self.object_list = self.get_queryset()
#         allow_empty = self.get_allow_empty()


def some_streaming_csv_view(request):
    """A view that streams a large CSV file."""
    # Generate a sequence of rows. The range is based on the maximum number of
    # rows that can be handled by a single sheet in most spreadsheet
    # applications.
    rows = (["Row {}".format(idx), str(idx)] for idx in range(65536))
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                     content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="somefilename.csv"'
    return response
