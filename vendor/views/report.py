import csv

from itertools import chain
from django.contrib import messages
from django.contrib.sites.models import Site
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import BaseListView
from django.views.generic.edit import FormMixin

from vendor.forms import DateRangeForm
from vendor.models import Receipt, Invoice, CustomerProfile
from vendor.utils import get_site_from_request


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
        # TODO: Figure out what to prepend the header without breaking the streaming generator
        response = StreamingHttpResponse((writer.writerow(row) for row in rows), content_type="text/csv")

        # Set the filename
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.filename)
        return response


class ReceiptListCSV(FormMixin, CSVStreamRowView):
    filename = "receipts.csv"
    model = Receipt
    form_class = DateRangeForm
    header = [[_('Order ID'), _('Title'), _('Order Date'), _('Order Status'), _('Order Total'), _('Product ID'), _('Product Name'), _('Quantity'), _('Item Cost'), _('Item Total'), _('Discount Amount '), _('Coupon Code'), _('Coupons Used'), _('Total Discount Amount'), _('Refund ID'), _('Refund Total'), _('Refund Amounts'), _('Refund Reason'), _('Refund Date'), _('Refund Author Email'), _('Date Type'), _('Dates')]]

    def get_queryset(self):
        form = self.form_class(data=self.request.POST)
        start_date = form.data.get('start_date', None)
        end_date = form.data.get('end_date', None)
        if start_date and end_date:
            return self.model.objects.filter(profile__site=Site.objects.get_current(), order_item__invoice__created__gte=start_date, order_item__invoice__created__lte=end_date)
        elif start_date and not end_date:
            return self.model.objects.filter(profile__site=Site.objects.get_current(), order_item__invoice__created__gte=start_date)
        else:
            return self.model.objects.filter(profile__site=Site.objects.get_current())      # Return receipts only for profiles on this site

    def get_row_data(self):
        object_list = self.get_queryset()
        rows = [[
            str(obj.order_item.invoice.pk),              # Order ID
            obj.order_item.invoice,                      # Title
            obj.order_item.invoice.created.isoformat(),  # Oder Date
            obj.get_status_display(),                    # Order Status
            obj.order_item.invoice.total,                # Order Total
            str(obj.products.first().id),                # Product ID
            obj.products.first().name,                   # Product Name
            obj.order_item.quantity,                     # Quantity
            obj.order_item.price,                        # Item Cost
            obj.order_item.total,                        # Item Total
            "",                                          # TODO: Discount Amount
            "",                                          # TODO: Coupon Code
            "",                                          # TODO: Coupons Used
            "",                                          # TODO: Total Discount Amount
            "",                                          # TODO: Refund ID
            "",                                          # TODO: Refund Total
            "",                                          # TODO: Refound Amounts
            "",                                          # TODO: Refund Reason
            "",                                          # TODO: Refund Date
            "",                                          # TODO: Refund Author Email
            'multiple' if obj.end_date is None else f'range',                                          # TODO: Date Type
            " ".join([ '' if obj.start_date is None else f'{obj.start_date:%Y-%m-%d}', '' if obj.end_date is None else f'{obj.end_date:%Y-%m-%d}']),
            ] for obj in object_list]
        return chain(self.header, rows)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if not form.is_valid():
            messages.info(self.request, ",".join([error for error in form.errors]))
            return redirect(request.META.get('HTTP_REFERER', self.success_url))

        rows = self.get_row_data()
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        # TODO: Figure out what to prepend the header without breaking the streaming generator
        response = StreamingHttpResponse((writer.writerow(row) for row in rows), content_type="text/csv")

        # Set the filename
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.filename)
        return response


class InvoiceListCSV(CSVStreamRowView):
    filename = "invoices.csv"
    model = Invoice

    def get_queryset(self):
        # TODO: Update to handle ranges from a POST
        if hasattr(self.request, 'site'):
            return self.model.objects.filter(site=get_site_from_request(self.request))
        return self.model.on_site.all()

    def get_row_data(self):
        object_list = self.get_queryset()
        header = [["INVOICE_ID", "CREATED_TIME(ISO)", "USERNAME", "CURRENCY", "TOTAL"]]  # Has to be a list inside an iterable (another list) for the chain to work.
        rows = ([str(obj.pk), obj.created.isoformat(), str(obj.profile.user.username), obj.currency, obj.total] for obj in object_list)
        return chain(header, rows)
