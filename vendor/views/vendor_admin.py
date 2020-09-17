from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView

from vendor.config import VENDOR_PRODUCT_MODEL
from vendor.models import Invoice, Offer, CustomerProfile
from vendor.forms import ProductForm, OfferForm

Product = apps.get_model(VENDOR_PRODUCT_MODEL)

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

class AdminProductListView(LoginRequiredMixin, ListView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/products.html"
    model = Product
    
    def get_queryset(self, **kwargs):
        return Product.objects.filter(site=CustomerProfile.objects.get(user=self.request.user).site)


class AdminProductUpdateView(LoginRequiredMixin, UpdateView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/product.html"
    model = Product
    form_class = ProductForm
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def form_valid(self, form):
        product = form.save(commit=False)
        product.save()
        return redirect('vendor_admin:manager-product-list')


class AdminProductCreateView(LoginRequiredMixin, CreateView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/product.html"
    form_class = ProductForm

    def form_valid(self, form):
        product = form.save(commit=False)
        product.save()
        return redirect('vendor_admin:manager-product-list')

class AdminOfferListView(LoginRequiredMixin, ListView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/offers.html"
    model = Offer


class AdminOfferUpdateView(LoginRequiredMixin, UpdateView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/offer.html"
    model = Offer
    form_class = OfferForm
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def form_valid(self, form):
        offer = form.save(commit=False)
        offer.save()

class AdminOfferCreateView(LoginRequiredMixin, CreateView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/offer.html"
    form_class = OfferForm    

    def form_valid(self, form):
        offer = form.save(commit=False)
        offer.save()
        return redirect('vendor_admin:manager-offer-list')