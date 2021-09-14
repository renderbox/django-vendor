from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from django.utils.translation import ugettext as _

from vendor.config import VENDOR_PRODUCT_MODEL
from vendor.forms import OfferForm, PriceFormSet, CreditCardForm, AddressForm
from vendor.models import Invoice, Offer, Receipt, CustomerProfile, Payment
from vendor.models.choice import TermType, PaymentTypes
from vendor.views.mixin import PassRequestToFormKwargsMixin, SiteOnRequestFilterMixin, TableFilterMixin, get_site_from_request
from vendor.processors import PaymentProcessor

Product = apps.get_model(VENDOR_PRODUCT_MODEL)

payment_processor = PaymentProcessor
#############
# Admin Views


class AdminDashboardView(LoginRequiredMixin, SiteOnRequestFilterMixin, ListView):
    '''
    List of the most recent invoices generated on the current site.
    '''
    template_name = "vendor/manage/dashboard.html"
    model = Invoice

    def get_queryset(self):
        """
        Return the most recent 10
        """
        queryset = super().get_queryset()

        return queryset[:10]


class AdminInvoiceListView(LoginRequiredMixin, SiteOnRequestFilterMixin, ListView):
    '''
    List of all the invoices generated on the current site.
    '''
    template_name = "vendor/manage/invoice_list.html"
    model = Invoice

    def get_queryset(self):
        """
        Ignores Cart state invoices
        """
        queryset = super().get_queryset()
        return queryset.order_by('updated')


class AdminInvoiceDetailView(LoginRequiredMixin, DetailView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/manage/invoice_detail.html"
    model = Invoice
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'


class AdminProductListView(LoginRequiredMixin, TableFilterMixin, SiteOnRequestFilterMixin, ListView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/manage/products.html"
    model = Product
    paginate_by = 25

    def search_filter(self, queryset):
        return queryset.filter(name__icontains=self.request.GET.get('search_filter'))


class AdminProductUpdateView(LoginRequiredMixin, UpdateView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/manage/product.html"
    model = Product
    fields = ['sku', 'name', 'site', 'available', 'description', 'meta']
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'
    success_url = reverse_lazy('vendor_admin:manager-product-list')


class AdminProductCreateView(LoginRequiredMixin, CreateView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/manage/product.html"
    model = Product
    fields = ['sku', 'name', 'site', 'available', 'description', 'meta']
    success_url = reverse_lazy('vendor_admin:manager-product-list')

    def form_valid(self, form):
        new_product = form.save(commit=False)
        new_product.save()
        return redirect(self.success_url)


class AdminOfferListView(LoginRequiredMixin, SiteOnRequestFilterMixin, ListView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/manage/offers.html"
    model = Offer


class AdminOfferUpdateView(LoginRequiredMixin, PassRequestToFormKwargsMixin, UpdateView):
    '''
    Details of an invoice generated on the current site.
    '''
    template_name = "vendor/manage/offer.html"
    model = Offer
    form_class = OfferForm
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'
    template_name_suffix = '_update_form'

    def get_initial(self):
        return {'products': self.object.products.all()}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        offer_products = self.object.products.all()
        customers_who_own = CustomerProfile.objects.filter(
            receipts__products__in=offer_products)
        customers_who_dont_own = CustomerProfile.objects.all().exclude(
            pk__in=[customer_profile.pk for customer_profile in customers_who_own.all()])

        context['customers_who_own'] = customers_who_own
        context['customers_who_dont_own'] = customers_who_dont_own

        context['formset'] = PriceFormSet(instance=self.object)

        return context

    def form_valid(self, form):
        price_formset = PriceFormSet(
            self.request.POST, self.request.FILES, instance=Offer.objects.get(uuid=self.kwargs['uuid']))

        offer = form.save(commit=False)

        if len(form.cleaned_data['products']) > 1:
            offer.bundle = True
        offer.save()

        for product in form.cleaned_data['products']:
            offer.products.add(product)

        if price_formset.has_changed() and not price_formset.is_valid():
            return render(self.request, self.template_name, {'form': form, 'formset': price_formset})
        elif price_formset.is_valid():
            for price_form in price_formset:
                price = price_form.save(commit=False)
                price.offer = offer
                if price_form.cleaned_data['price_select'] == 'free':
                    price.cost = 0
                price.save()
        else:
            return render(self.request, self.template_name, {'form': form, 'formset': price_formset})

        return redirect('vendor_admin:manager-offer-list')


class AdminOfferCreateView(LoginRequiredMixin, PassRequestToFormKwargsMixin, CreateView):
    '''
    Creates a Product to be added to offers
    '''
    template_name = "vendor/manage/offer.html"
    model = Offer
    form_class = OfferForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['formset'] = PriceFormSet()

        return context

    def post(self, request):
        offer_form = self.form_class(request.POST, request=request)
        price_formset = PriceFormSet(request.POST)

        if not offer_form.is_valid():
            return render(request, self.template_name, {'form': offer_form, 'formset': price_formset})

        offer = offer_form.save(commit=False)
        if len(offer_form.cleaned_data['products']) > 1:
            offer.bundle = True

        offer.save()
        for product in offer_form.cleaned_data['products']:
            offer.products.add(product)

        if price_formset.has_changed() and not price_formset.is_valid():
            return render(request, self.template_name, {'form': offer_form, 'formset': price_formset})
        elif price_formset.has_changed() and price_formset.is_valid():
            product_currencies = {}
            # price_currency = [price_form.cleaned_data['currency']
            #                   for price_form in price_formset]

            for product in Product.objects.filter(pk__in=offer_form.cleaned_data['products']):
                for currency in product.meta['msrp'].keys():
                    product_currencies[currency] = currency

            for price_form in price_formset:
                if price_form.cleaned_data['currency'] not in product_currencies:
                    price_formset[0].add_error(
                        'currency', _('Invalid currency'))
                    return render(request, self.template_name, {'form': offer_form, 'formset': price_formset})

            for price_form in price_formset:
                price = price_form.save(commit=False)
                if price_form.cleaned_data['price_select'] == 'free':
                    price.cost = 0
                price.offer = offer
                price.save()

        return redirect('vendor_admin:manager-offer-list')


class AdminSubscriptionListView(LoginRequiredMixin, ListView):
    '''
    List of all the invoices generated on the current site.
    '''
    template_name = "vendor/manage/receipt_list.html"
    model = Receipt

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(products__in=Product.on_site.all(), order_item__offer__terms__lt=TermType.PERPETUAL)


class AdminSubscriptionDetailView(LoginRequiredMixin, DetailView):
    '''
    Gets all Customer Profile information for quick lookup and management
    '''
    template_name = 'vendor/manage/subscription_detail.html'
    model = Receipt
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = Payment.objects.get(transaction=context['object'].transaction)

        context['payment'] = payment
        context['payment_form'] = CreditCardForm(
            initial={'payment_type': PaymentTypes.CREDIT_CARD})
        context['billing_form'] = AddressForm(instance=payment.billing_address)

        return context


class AdminProfileListView(LoginRequiredMixin, SiteOnRequestFilterMixin, ListView):
    """
    List of CustomerProfiles on site
    """
    template_name = "vendor/manage/profile_list.html"
    model = CustomerProfile


class AdminProfileDetailView(LoginRequiredMixin, DetailView):
    '''
    Gets all Customer Profile information for quick lookup and management
    '''
    template_name = 'vendor/manage/profile_detail.html'
    model = CustomerProfile
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['free_offers'] = Offer.objects.filter(prices__cost=0, site=self.object.site)

        return context


class VoidProductView(LoginRequiredMixin, View):
    success_url = reverse_lazy('vendor_admin:manage-profiles')

    def post(self, request, *args, **kwargs):
        receipt = Receipt.objects.get(uuid=self.kwargs["uuid"])
        receipt.void()
        receipt.save()

        messages.info(request, _("Customer has no longer access to Product"))
        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class AddOfferToProfileView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        customer_profile = CustomerProfile.objects.get(uuid=kwargs.get('uuid_profile'))
        offer = Offer.objects.get(uuid=kwargs['uuid_offer'])

        cart = customer_profile.get_cart_or_checkout_cart()
        cart.empty_cart()
        cart.add_offer(offer)

        if offer.current_price() or cart.total:
            messages.info(request, _("Offer and Invoice must have zero value"))
            cart.remove_offer(offer)
            return redirect(reverse('vendor_admin:manager-profile', kwargs={'uuid': customer_profile.uuid}))

        processor = payment_processor(cart)
        processor.authorize_payment()

        messages.info(request, _("Offer Added To Customer Profile"))
        return redirect(reverse('vendor_admin:manager-profile', kwargs={'uuid': customer_profile.uuid}))


class ProductAvailabilityToggleView(LoginRequiredMixin, View):
    success_url = reverse_lazy('vendor_admin:manager-product-list')

    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, uuid=self.kwargs.get('uuid'))

        product.available = request.POST.get('available', False)
        product.save()

        for offer in Offer.objects.filter(products__in=[product]):
            offer.available = product.available
            offer.save()

        messages.info(request, _("Product availability Changed"))
        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class AdminManualSubscriptionRenewal(LoginRequiredMixin, DetailView):
    success_url = reverse_lazy('vendor_admin:manage-profiles')
    model = Receipt
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def post(self, request, *args, **kwargs):
        past_receipt = Receipt.objects.get(uuid=self.kwargs["uuid"])

        payment_info = {
            'msg': 'renewed manually'
        }

        invoice = Invoice(status=Invoice.InvoiceStatus.PROCESSING, site=past_receipt.order_item.invoice.site)
        invoice.profile = past_receipt.profile
        invoice.save()
        invoice.add_offer(past_receipt.order_item.offer)

        processor = PaymentProcessor(invoice)
        processor.renew_subscription(past_receipt, payment_info)

        messages.info(request, _("Subscription Renewed"))
        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class PaymentWithNoReceiptListView(LoginRequiredMixin, ListView):
    template_name = "vendor/manage/payment_list.html"
    model = Payment

    def get_queryset(self):
        site = get_site_from_request(self.request)
        return [payment for payment in Payment.objects.filter(invoice__site=site, success=True) if payment.get_receipt() is None]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Payments with no Receipts")
        return context


class PaymentWithNoOrderItemsListView(LoginRequiredMixin, ListView):
    template_name = "vendor/manage/payment_list.html"
    model = Payment

    def get_queryset(self):
        site = get_site_from_request(self.request)
        return Payment.objects.filter(invoice__site=site, success=True).annotate(order_item_count=Count('invoice__order_items')).filter(order_item_count=0)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Payments with no Order Items")
        return context
