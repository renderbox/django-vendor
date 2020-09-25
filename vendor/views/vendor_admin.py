from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from vendor.config import VENDOR_PRODUCT_MODEL
from vendor.models import Invoice, Offer, Price
from vendor.forms import ProductForm, OfferForm, PriceForm, PriceFormSet

Product = apps.get_model(VENDOR_PRODUCT_MODEL)
#############
# Admin Views

class AdminDashboardView(LoginRequiredMixin, ListView):
    '''
    List of the most recent invoices generated on the current site.
    '''
    template_name = "vendor/manage/dashboard.html"
    model = Invoice

    def get_queryset(self):
        return self.model.on_site.all()[:10]    # Return the most recent 10


class AdminInvoiceListView(LoginRequiredMixin, ListView):
    '''
    List of all the invoices generated on the current site.
    '''
    template_name = "vendor/manage/invoice_list.html"
    model = Invoice

    def get_queryset(self):
        return self.model.on_site.filter(status__gt=Invoice.InvoiceStatus.CART)  # ignore cart state invoices


class AdminInvoiceDetailView(LoginRequiredMixin, DetailView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/manage/invoice_detail.html"
    model = Invoice
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'


class AdminProductListView(LoginRequiredMixin, ListView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/manage/products.html"
    model = Product
    queryset = Product.on_site.all()


class AdminProductUpdateView(LoginRequiredMixin, UpdateView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/manage/product.html"
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
    template_name = "vendor/manage/product.html"
    form_class = ProductForm

    def form_valid(self, form):
        product = form.save(commit=False)
        product.save()
        return redirect('vendor_admin:manager-product-list')

class AdminOfferListView(LoginRequiredMixin, ListView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/manage/offers.html"
    model = Offer
    queryset = Offer.on_site.all()


class AdminOfferUpdateView(LoginRequiredMixin, UpdateView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/manage/offer.html"
    model = Offer
    form_class = OfferForm
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['formset'] = PriceFormSet(instance=Offer.objects.get(uuid=context['view'].kwargs['uuid']))

        return context


    def form_valid(self, form):
        price_formset = PriceFormSet(self.request.POST, self.request.FILES, instance=Offer.objects.get(uuid=self.kwargs['uuid']))

        if not (price_formset.is_valid() or form.is_valid()):
            return render(self.request, self.template_name, {'form': form, 'formsert': price_formset})

        offer = form.save(commit=False)

        if len(form.cleaned_data['products']):
            offer.bundle=True
        
        offer.save()

        for product in form.cleaned_data['products']:
            offer.products.add(product)

        for price_form in price_formset:
            price = price_form.save(commit=False)
            price.offer = offer
            price.save()

        return redirect('vendor_admin:manager-offer-list')


class AdminOfferCreateView(LoginRequiredMixin, CreateView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/manage/offer.html"
    form_class = OfferForm    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['formset'] = PriceFormSet()

        return context

    def post(self, request):
        offer_form = self.form_class(request.POST)
        price_formset = PriceFormSet(request.POST)

        if not (price_formset.is_valid() and offer_form.is_valid()):
            return render(request, self.template_name, {'form': offer_form, 'formsert': price_formset})

        offer = offer_form.save(commit=False)
        if len(offer_form.cleaned_data['products']):
            offer.bundle=True

        offer.save()
        for product in offer_form.cleaned_data['products']:
            offer.products.add(product)


        for price_form in price_formset:
            price = price_form.save(commit=False)
            price.offer = offer
            price.save()

        return redirect('vendor_admin:manager-offer-list')