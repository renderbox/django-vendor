from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView

from vendor.models import Invoice



#############
# Admin Views

class AdminDashboardView(LoginRequiredMixin, ListView):
    '''
    List of the most recent invoices generated on the current site.
    '''
    template_name = "vendor/admin_dashboard.html"
    model = Invoice

    def get_queryset(self):
        return self.model.on_site.all()[:10]    # Return the most recent 10


class AdminInvoiceListView(LoginRequiredMixin, ListView):
    '''
    List of all the invoices generated on the current site.
    '''
    template_name = "vendor/invoice_admin_list.html"
    model = Invoice

    def get_queryset(self):
        return self.model.on_site.filter(status__gt=Invoice.InvoiceStatus.CART)  # ignore cart state invoices


class AdminInvoiceDetailView(LoginRequiredMixin, DetailView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/invoice_admin_detail.html"
    model = Invoice
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'
