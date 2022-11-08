import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, Http404
from django.utils.translation import gettext as _
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View, FormView
from django.views.generic.edit import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView


from vendor.forms import BillingAddressForm, CreditCardForm, AccountInformationForm, AddressForm
from vendor.models import Offer, Invoice, Address, OrderItem, Receipt, Subscription
from vendor.models.choice import TermType, PurchaseStatus, InvoiceStatus
from vendor.processors import get_site_payment_processor
from vendor.utils import get_site_from_request, get_or_create_session_cart, clear_session_purchase_data

logger = logging.getLogger(__name__)


# TODO: Need to remove the login required
def get_purchase_invoice(user, site):
    """
    Return an invoice that is in checkout or cart state or a newly create invoice in cart state.
    """
    profile, created = user.customer_profile.get_or_create(site=site)
    return profile.get_cart_or_checkout_cart()


def check_offer_items_or_redirect(invoice, request):

    if invoice.order_items.count() < 1:
        messages.info(request, _("Please add to your cart"))
        redirect('vendor:cart')


class VendorHomeView(TemplateView):
    template_name = 'vendor/index.html'


class CartView(TemplateView):
    '''
    View items in the cart
    '''
    template_name = 'vendor/invoice_detail.html'

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        if request.user.is_anonymous:
            session_cart = get_or_create_session_cart(request.session)

            context['invoice'] = {}
            if len(session_cart):
                context['order_items'] = [ OrderItem(offer=Offer.objects.get(pk=offer), quantity=session_cart[offer]['quantity']) for offer in session_cart.keys() ]
            else:
                context['order_items'] = []
            context['invoice']['subtotal'] = sum([item.total for item in context['order_items'] ])
            context['invoice']['shipping'] = 0
            context['invoice']['tax'] = 0
            context['invoice']['total'] = context['invoice']['subtotal']

            return render(request, self.template_name, context)

        profile, created = self.request.user.customer_profile.get_or_create(site=get_site_from_request(request))
        cart = profile.get_cart_or_checkout_cart()
        context['invoice'] = cart
        context['order_items'] = [ order_item for order_item in cart.order_items.all() ]
        return render(request, self.template_name, context)


class AccountInformationView(LoginRequiredMixin, TemplateView):
    template_name = 'vendor/checkout.html'

    def get_form_class(self):
        return AccountInformationForm

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        clear_session_purchase_data(request)

        invoice = get_purchase_invoice(request.user, get_site_from_request(request))
        
        if not invoice.order_items.count():
            return redirect('vendor:cart')

        invoice.status = InvoiceStatus.CHECKOUT
        invoice.save()

        existing_account_address = Address.objects.filter(profile__user=request.user, profile__site=get_site_from_request(request)).last()

        form_class = self.get_form_class()
        if existing_account_address:
            # TODO: In future the user will be able to select from multiple saved address
            form = form_class(initial={'email': request.user.email}, instance=existing_account_address)
        else:
            form = form_class(initial={'first_name': request.user.first_name, 'last_name': request.user.last_name, 'email': request.user.email})

        context['form'] = form
        context['invoice'] = invoice

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.get_form_class()(request.POST)
        invoice = get_purchase_invoice(request.user, get_site_from_request(request))

        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'invoice': invoice})

        shipping_address = form.save(commit=False)

        if not invoice.order_items.count() or invoice.status == InvoiceStatus.CART:
            messages.info(request, _("Cart changed while in checkout process"))
            return redirect('vendor:cart')

        invoice.status = InvoiceStatus.CHECKOUT
        invoice.customer_notes = {'remittance_email': form.cleaned_data['email']}
        # TODO: Need to add a drop down to select existing address
        shipping_address, created = invoice.profile.get_or_create_address(shipping_address)

        if created:
            shipping_address.profile = invoice.profile
            shipping_address.save()
        invoice.shipping_address = shipping_address
        invoice.save()

        return redirect('vendor:checkout-payment')


class PaymentView(LoginRequiredMixin, TemplateView):
    '''
    Review items and submit Payment
    '''
    template_name = "vendor/checkout.html"

    def get(self, request, *args, **kwargs):
        invoice = get_purchase_invoice(request.user, get_site_from_request(request))

        if not invoice.order_items.count():
            return redirect('vendor:cart')

        context = super().get_context_data()

        processor = get_site_payment_processor(invoice.site)(invoice.site, invoice)

        context = processor.get_checkout_context(context=context)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = get_purchase_invoice(request.user, get_site_from_request(request))

        if not invoice.order_items.count() or invoice.status == InvoiceStatus.CART:
            messages.info(request, _("Cart changed while in checkout process"))
            return redirect('vendor:cart')

        credit_card_form = CreditCardForm(request.POST)
        
        if request.POST.get('billing-same_as_shipping') == 'on':
            billing_address_form = BillingAddressForm(instance=invoice.shipping_address)
            billing_address_form.data = {f'billing-{key}': value for key, value in billing_address_form.initial.items()}
            billing_address_form.is_bound = True
        else:
            billing_address_form = BillingAddressForm(request.POST)

        if not (billing_address_form.is_valid() and credit_card_form.is_valid()):
            processor = get_site_payment_processor(invoice.site)(invoice.site, invoice)
            context['billing_address_form'] = billing_address_form
            context['credit_card_form'] = credit_card_form
            return render(request, self.template_name, processor.get_checkout_context(context=context))
        else:
            billing_address_form.full_clean()
            credit_card_form.full_clean()
            request.session['billing_address_form'] = {f'billing-{key}': value for key, value in billing_address_form.cleaned_data.items()}
            request.session['credit_card_form'] = credit_card_form.cleaned_data
            return redirect('vendor:checkout-review')


class ReviewCheckoutView(LoginRequiredMixin, TemplateView):
    template_name = 'vendor/checkout.html'

    def get(self, request, *args, **kwargs):
        invoice = get_purchase_invoice(request.user, get_site_from_request(request))
        if not invoice.order_items.count():
            return redirect('vendor:cart')

        context = super().get_context_data()

        processor = get_site_payment_processor(invoice.site)(invoice.site, invoice)
        if 'billing_address_form' in request.session:
            billing_address_form = BillingAddressForm(request.session['billing_address_form'])
            billing_address_form.is_valid()
            context['billing_address_form'] = billing_address_form
        if 'credit_card_form' in request.session:
            context['credit_card_form'] = CreditCardForm(request.session['credit_card_form'])

        context = processor.get_checkout_context(context=context)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # context = super().get_context_data(**kwargs)
        invoice = get_purchase_invoice(request.user, get_site_from_request(request))
        if not invoice.order_items.count() or invoice.status == InvoiceStatus.CART:
            messages.info(request, _("Cart changed while in checkout process"))
            return redirect('vendor:cart')

        processor = get_site_payment_processor(invoice.site)(invoice.site, invoice)

        processor.set_billing_address_form_data(request.session.get('billing_address_form'), BillingAddressForm)
        processor.set_payment_info_form_data(request.session.get('credit_card_form'), CreditCardForm)

        processor.authorize_payment()

        if processor.transaction_succeeded:
            return redirect('vendor:purchase-summary', uuid=invoice.uuid)
        else:
            logger.warning(f"Payment gateway did not authorize payment {processor.transaction_info}")
            # TODO: Make message configurable for the site in the settings
            messages.info(self.request, _("The payment gateway did not authorize payment."))
            return redirect('vendor:checkout-account')


class PaymentSummaryView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'vendor/payment_summary.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        context['payment'] = self.object.payments.filter(success=True).first()
        return context


class OrderHistoryListView(LoginRequiredMixin, ListView):
    '''
    List of all the invoices generated by the current user on the current site.
    '''
    model = Invoice
    # TODO: filter to only include the current user's order history

    def get_queryset(self):
        try:
            # The profile and user are site specific so this should only return what's on the site for that user excluding the cart
            return self.request.user.customer_profile.get(site=get_site_from_request(self.request)).invoices.filter(status__gt=InvoiceStatus.CART)
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


class ReceiptListView(LoginRequiredMixin, ListView):
    model = Receipt
    template_name = 'vendor/purchase_list.html'

    def get_queryset(self):
        return self.request.user.customer_profile.get(site=get_site_from_request(self.request)).receipts.all()


class ReceiptDetailView(LoginRequiredMixin, DetailView):
    model = Receipt
    template_name = 'vendor/purchase_detail.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        context['payment'] = self.object.order_item.invoice.payments.get(success=True, transaction=self.object.transaction)

        return context


class SubscriptionsListView(LoginRequiredMixin, ListView):
    model = Receipt
    template_name = 'vendor/purchase_list.html'

    def get_queryset(self):
        try:
            receipts = self.request.user.customer_profile.get(site=get_site_from_request(self.request)).receipts.filter(auto_renew=True)
        except ObjectDoesNotExist:
            raise Http404(_("Not Found"))
        
        subscriptions = [ receipt for receipt in receipts.all() if receipt.order_item.offer.terms > TermType.PERPETUAL and receipt.order_item.offer.terms < TermType.ONE_TIME_USE ]
        
        return subscriptions


class SubscriptionUpdatePaymentView(LoginRequiredMixin, FormView):
    form_class = CreditCardForm()
    success_url = reverse_lazy('vendor:customer-subscriptions')

    def post(self, request, *args, **kwargs):
        subscription = Subscription.objects.get(uuid=self.kwargs["uuid"])
        payment_form = CreditCardForm(request.POST)

        if not payment_form.is_valid():
            messages.info(request, _("Invalid Card"))
            return redirect(request.META.get('HTTP_REFERER', self.success_url))

        processor = get_site_payment_processor(subscription.profile.site)(subscription.profile.site)
        processor.set_payment_info_form_data(request.POST, CreditCardForm)
        processor.subscription_update_payment(subscription)

        if not processor.transaction_succeeded:
            messages.info(request, _(f"Payment gateway error: {processor.transaction_info.get('errors', '')}"))
            return redirect(request.META.get('HTTP_REFERER', self.success_url))

        messages.info(request, _("Success: Payment Updated"))
        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class AddressUpdateView(LoginRequiredMixin, FormView):
    form_class = BillingAddressForm

    def post(self, request, *args, **kwargs):
        address_form = AddressForm(request.POST)
        address = Address.objects.get(uuid=self.kwargs['uuid'])

        if not address_form.is_valid():
            messages.info(request, _(f"Failed: {address_form.errors}"))
        else:
            messages.info(request, _("Success: Address Updated"))
            update_address = address_form.save(commit=False)
            address.first_name = update_address.first_name
            address.last_name = update_address.last_name
            address.address_1 = update_address.address_1
            address.address_2 = update_address.address_2
            address.locality = update_address.locality
            address.state = update_address.state
            address.country = update_address.country
            address.postal_code = update_address.postal_code
            address.save()

        return redirect(request.META.get('HTTP_REFERER', self.success_url))


class ShippingAddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    fields = '__all__'
    template_name_suffix = '_update_form'
    template_name = 'vendor/address_detail.html'
    success_url = reverse_lazy('vendor:products')

    def get_success_url(self):
        messages.info(self.request, _("Shipping Address Updated"))
        return self.request.META.get('HTTP_REFERER', self.success_url)
