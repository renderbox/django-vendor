import csv
from itertools import chain

from django.http import StreamingHttpResponse
from django.utils.timezone import localtime
from django.contrib.sites.models import Site
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic.list import BaseListView

from vendor.models import Receipt, Invoice


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """
    
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


class CSVStreamRowView(BaseListView):
    """A base view for displaying a list of objects."""

    filename = "receipt_list.csv"
    # headers = 

    def get_queryset(self):
        return super().get_queryset()
    
    def get_row_data(self):
        header = [["ROW_NAME", "ROW_COUNT"]]  # Has to be a list inside an iterable (another list) for the chain to work.
        rows = (["Row {}".format(idx), str(idx)] for idx in range(500))     # Dummy data to show that its working.
        return chain(header, rows)

    def get(self, request, *args, **kwargs):
        rows = self.get_row_data()
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        #TODO: Figure out what to prepend the header without breaking the streaming generator
        response = StreamingHttpResponse((writer.writerow(row) for row in rows), content_type="text/csv")

        # Set the filename
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.filename)
        return response


class ReceiptListCSV(CSVStreamRowView):
    filename = "receipts.csv"
    model = Receipt

    def get_queryset(self):
        # TODO: Update to handle ranges from a POST
        return self.model.objects.filter(profile__site=Site.objects.get_current())      # Return receipts only for profiles on this site

    def get_row_data(self):
        object_list = self.get_queryset()
        header = [["receipt_ID", "CREATED_TIME(ISO)", "USERNAME", "INVOICE_ID", "ORDER_ITEM", "OFFER_ID", "QUANTITY", "TRANSACTION_ID", "STATUS"]]  # Has to be a list inside an iterable (another list) for the chain to work.
        rows = [[str(obj.pk), obj.created.isoformat(), obj.profile.user.username, obj.order_item.invoice.pk, obj.order_item.offer, obj.order_item.pk, obj.order_item.quantity, obj.transaction, obj.get_status_display()] for obj in object_list]
        return chain(header, rows)

 
class InvoiceListCSV(CSVStreamRowView):
    filename = "invoices.csv"
    model = Invoice

    def get_queryset(self):
        # TODO: Update to handle ranges from a POST
        return self.model.on_site.all()
    
    def get_row_data(self):
        object_list = self.get_queryset()
        header = [["INVOICE_ID", "CREATED_TIME(ISO)", "USERNAME", "CURRENCY", "TOTAL"]]  # Has to be a list inside an iterable (another list) for the chain to work.
        rows = ([str(obj.pk), obj.created.isoformat(), str(obj.profile.user.username), obj.currency, obj.total] for obj in object_list)
        return chain(header, rows)
