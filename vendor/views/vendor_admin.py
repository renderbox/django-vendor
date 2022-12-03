import logging

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.db import IntegrityError, DatabaseError, transaction
from django.db.models import Count, Q
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import View, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, FormView, ProcessFormView, FormMixin, ModelFormMixin
from django.views.generic.list import ListView
from django.utils import timezone
from django.utils.translation import gettext as _

from vendor.config import VENDOR_PRODUCT_MODEL, PaymentProcessorSiteConfig,\
    PaymentProcessorSiteSelectSiteConfig, PaymentProcessorForm, PaymentProcessorSiteSelectForm

from vendor.forms import OfferForm, PriceFormSet, CreditCardForm, AddressForm,\
    AuthorizeNetIntegrationForm, StripeIntegrationForm, SubscriptionForm,\
    SiteSelectForm, SubscriptionAddPaymentForm, OfferSiteSelectForm

from vendor.integrations import AuthorizeNetIntegration, StripeIntegration
from vendor.models import Invoice, Offer, Receipt, CustomerProfile, Payment, Subscription
from vendor.models.choice import TermType, PaymentTypes, InvoiceStatus, PurchaseStatus, SubscriptionStatus
from vendor.views.mixin import PassRequestToFormKwargsMixin, SiteOnRequestFilterMixin, TableFilterMixin, get_site_from_request
from vendor.processors import get_site_payment_processor
from vendor.utils import get_subscription_start_date, get_payment_scheduled_end_date
from siteconfigs.models import SiteConfigModel

Product = apps.get_model(VENDOR_PRODUCT_MODEL)
logger = logging.getLogger(__name__)


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
    model = Subscription

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset


class AdminSubscriptionDetailView(LoginRequiredMixin, DetailView):
    '''
    Gets all Customer Profile information for quick lookup and management
    '''
    template_name = 'vendor/manage/subscription_detail.html'
    model = Subscription
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscription = context['object']
        payment = subscription.payments.first()

        context['payment'] = payment
        context['payment_form'] = CreditCardForm(
            initial={'payment_type': PaymentTypes.CREDIT_CARD}
        )
        if payment and payment.billing_address:
            context['billing_form'] = AddressForm(instance=payment.billing_address)

        context['payments'] = subscription.payments.order_by('-submitted_date')
        context['receipts'] = subscription.receipts.order_by('-start_date')

        return context


class AdminSubscriptionCreateView(LoginRequiredMixin, TemplateView):
    '''
    Gets all Customer Profile information for quick lookup and management
    '''
    template_name = 'vendor/manage/subscription_create.html'
    success_url = reverse_lazy('vendor_admin:manager-subscription-create')

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if 'site' in request.GET:
            site_form = SiteSelectForm(request.GET)

            if not site_form.is_valid():
                context['site_form'] = site_form
                return render(request, self.template_name, context)
            
            context['subscription_form'] = SubscriptionForm(initial={'site': site_form.cleaned_data['site']})
            context['site_form'] = site_form

            return render(request, self.template_name, context)

        context['site_form'] = SiteSelectForm()

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        subscription_form = SubscriptionForm(request.POST)
        
        if not subscription_form.is_valid():
            context['subscription_form'] = subscription_form
            return render(request, self.template_name, context)

        subscription = Subscription.objects.create(
            profile=subscription_form.cleaned_data['profile'],
            gateway_id=subscription_form.cleaned_data['subscription_id'],
            status=subscription_form.cleaned_data['status']
        )
        messages.info(request, _("Subscription Created"))

        return redirect(self.success_url)


class AdminSubscriptionAddPaymentView(LoginRequiredMixin, TemplateView):
    template_name = 'vendor/manage/subscription_add_payment.html'
    success_url = reverse_lazy('vendor_admin:manager-subscriptions')

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        subscription = Subscription.objects.get(uuid=kwargs.get('uuid_subscription'))
        profile = CustomerProfile.objects.get(uuid=kwargs.get('uuid_profile'))

        if 'site' in request.GET:
            offer_site_form = OfferSiteSelectForm(request.GET)

            if not offer_site_form.is_valid():
                context['offer_site_form'] = offer_site_form
                return render(request, self.template_name, context)
            
            context['form'] = SubscriptionAddPaymentForm(initial={
                'offer': offer_site_form.cleaned_data['offer'],
                'subscription': subscription,
                'profile': profile
            })
            
            context['offer_site_form'] = offer_site_form

            return render(request, self.template_name, context)

        context['offer_site_form'] = OfferSiteSelectForm()

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        offer_site_form = OfferSiteSelectForm(request.GET)

        if not offer_site_form.is_valid():
            context['offer_site_form'] = payment_form
            return render(request, self.template_name, context)

        payment_form = SubscriptionAddPaymentForm(request.POST, site=offer_site_form.cleaned_data['site'])

        if not payment_form.is_valid():
            context['form'] = payment_form
            return render(request, self.template_name, context)
        
        payment = payment_form.save(commit=False)
        offer = payment_form.cleaned_data['offer']

        invoice = payment.profile.get_cart_or_checkout_cart()
        invoice.empty_cart()
        invoice.status = InvoiceStatus.COMPLETE
        invoice.add_offer(offer)

        try:
            with transaction.atomic():
                payment.invoice = invoice
                payment.amount = invoice.total
                payment.save()

                if payment.success and payment.status == PurchaseStatus.SETTLED:
                    receipt = Receipt.objects.create(
                        transaction=payment.transaction,
                        order_item=invoice.order_items.first(),
                        profile=payment.profile,
                        start_date=get_subscription_start_date(offer, payment.profile, payment.submitted_date),
                        end_date=get_payment_scheduled_end_date(offer, payment.submitted_date),
                        subscription=payment.subscription
                    )

            messages.info(request, _("Payment Added to Subscription"))

        except (IntegrityError, DatabaseError, Exception) as exce:
            logger.error(f"AdminSubscriptionCreateView error: {exce}")
            messages.error(request, "failed to add payment to subscription")
            return render(request, self.template_name, context)

        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class AdminProfileListView(LoginRequiredMixin, TableFilterMixin, SiteOnRequestFilterMixin, ListView):
    """
    List of CustomerProfiles on site
    """
    template_name = "vendor/manage/profile_list.html"
    model = CustomerProfile
    paginate_by = 100


    def search_filter(self, queryset):
        search_value = self.request.GET.get('search_filter')
        return queryset.filter(Q(pk__icontains=search_value) | \
                               Q(user__email__icontains=search_value) | \
                               Q(user__username__icontains=search_value))

    def get_paginated_by(self, queryset):
        if 'paginate_by' in self.request.kwargs:
            return kwargs['paginate_by']
        return self.paginate_by
    
    def get_queryset(self):
        queryset = super().get_queryset()

        return queryset.order_by('pk')


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
        context['invoices'] = self.object.invoices.order_by("-created")

        return context


class AdminManualSubscriptionRenewal(LoginRequiredMixin, DetailView):
    success_url = reverse_lazy('vendor_admin:manage-profiles')
    model = Subscription
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def post(self, request, *args, **kwargs):
        subscription = Subscription.objects.get(uuid=self.kwargs["uuid"])
        submitted_datetime = timezone.now()

        invoice = Invoice.objects.create(
            profile=customer_profile,
            site=site,
            ordered_date=submitted_datetime,
            status=InvoiceStatus.COMPLETE
        )
        invoice.add_offer(offer)
        invoice.save()

        transaction_id = timezone.now().strftime("%Y-%m-%d_%H-%M-%S-Manual-Renewal")

        processor = get_site_payment_processor(invoice.site)(invoice.site, invoice)
        processor.renew_subscription(subscription, transaction_id, PurchaseStatus.CAPTURED)

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


class PaymentProcessorSiteConfigsListView(ListView):
    template_name = 'vendor/manage/processor_site_config_list.html'
    model = SiteConfigModel

    def get_queryset(self):
        payment_processor = PaymentProcessorSiteConfig()

        return SiteConfigModel.objects.filter(key=payment_processor.key)


class PaymentProcessorSiteFormView(SiteOnRequestFilterMixin, FormView):
    template_name = 'vendor/manage/processor_site_config.html'
    form_class = PaymentProcessorForm

    def get_success_url(self):
        return reverse('vendor_admin:vendor-site-processor')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        site = get_site_from_request(self.request)
        processor_config = PaymentProcessorSiteConfig(site)
        context['form'] = processor_config.get_form()

        return context

    def form_valid(self, form):
        site = get_site_from_request(self.request)
        processor_config = PaymentProcessorSiteConfig(site)
        processor_config.save(form.cleaned_data["payment_processor"], "payment_processor")

        return redirect('vendor_admin:vendor-processor-lists')


class PaymentProcessorSiteSelectFormView(FormView):
    template_name = 'vendor/manage/processor_site_config.html'
    form_class = PaymentProcessorSiteSelectForm

    def get_success_url(self):
        return reverse('vendor_admin:processor-lists')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        if self.kwargs.get('domain'):
            site = Site.objects.get(domain=self.kwargs.get('domain'))
            processor_config = PaymentProcessorSiteSelectSiteConfig(site)
        else:
            processor_config = PaymentProcessorSiteSelectSiteConfig()
        context['form'] = processor_config.get_form()

        return context

    def form_valid(self, form):
        site = Site.objects.get(pk=form.cleaned_data['site'])
        processor_config = PaymentProcessorSiteSelectSiteConfig(site)
        processor_config.save(form.cleaned_data["payment_processor"], "payment_processor")
        
        return redirect('vendor_admin:vendor-processor-lists')


class AuthorizeNetIntegrationView(FormView):
    template_name = "vendor/integration_form.html"
    form_class = AuthorizeNetIntegrationForm
    success_url = reverse_lazy('authorizenet-integration')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        authorizenet_integration = AuthorizeNetIntegration(get_site_from_request(self.request))
        context['integration_name'] = _("AuthorizeNet Integration")

        context['form'] = AuthorizeNetIntegrationForm(instance=authorizenet_integration.instance)

        return context
    
    def form_valid(self, form):
        authorizenet_integration = AuthorizeNetIntegration(get_site_from_request(self.request))
        authorizenet_integration.save(form.cleaned_data)

        return super().form_valid(form)


class StripeIntegrationView(FormView):
    template_name = "vendor/integration_form.html"
    form_class = StripeIntegrationForm
    success_url = reverse_lazy('stripe-integration')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        stripe_integration = StripeIntegration(get_site_from_request(self.request))
        context['integration_name'] = _("Stripe Integration")

        context['form'] = StripeIntegrationForm(instance=stripe_integration.instance)

        return context
    
    def form_valid(self, form):
        stripe_integration = StripeIntegration(get_site_from_request(self.request))
        stripe_integration.save(form.cleaned_data)

        return super().form_valid(form)

