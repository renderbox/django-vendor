from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist
from django.template import RequestContext

from django.views.generic.edit import DeleteView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView

from vendor.models import Offer, Invoice, Payment, Address, CustomerProfile
from vendor.models.choice import TermType
from vendor.models.utils import set_default_site_id
from vendor.processors import PaymentProcessor
from vendor.forms import BillingAddressForm, CreditCardForm, AccountInformationForm

# from vendor.models.address import Address as GoogleAddress

# The Payment Processor configured in settings.py
payment_processor = PaymentProcessor

# TODO: Need to remove the login required

def get_purchase_invoice(user):
    """
    Return an invoice that is in checkout or cart state or a newly create invoice in cart state.
    """
    profile, created = user.customer_profile.get_or_create(site=settings.SITE_ID)
    return profile.get_cart_or_checkout_cart()

def clear_session_purchase_data(request):
    if 'billing_address_form' in request.session:
        del(request.session['billing_address_form'])
    if 'credit_card_form' in request.session:
        del(request.session['credit_card_form'])

class CartView(LoginRequiredMixin, DetailView):
    '''
    View items in the cart
    '''
    model = Invoice

    def get_object(self):
        profile, created = self.request.user.customer_profile.get_or_create(
            site=set_default_site_id())
        return profile.get_cart_or_checkout_cart()


class AddToCartView(LoginRequiredMixin, TemplateView):
    '''
    Create an order item and add it to the order
    '''

    def post(self, request, *args, **kwargs):
        offer = Offer.objects.get(slug=self.kwargs["slug"])
        profile, created = self.request.user.customer_profile.get_or_create(
            site=set_default_site_id())

        cart = profile.get_cart_or_checkout_cart()

        if cart.status == Invoice.InvoiceStatus.CHECKOUT:
            messages.info(self.request, _("You have a pending cart in checkout"))
            return redirect(request.META.get('HTTP_REFERER'))

        cart.add_offer(offer)
        messages.info(self.request, _("Added item to cart."))

        return redirect('vendor:cart')      # Redirect to cart on success


class RemoveFromCartView(LoginRequiredMixin, DeleteView):
    
    def post(self, request, *args, **kwargs):
        offer = Offer.objects.get(slug=self.kwargs["slug"])
        profile = self.request.user.customer_profile.get(
            site=settings.SITE_ID)      # Make sure they have a cart

        cart = profile.get_cart_or_checkout_cart()

        if cart.status == Invoice.InvoiceStatus.CHECKOUT:
            messages.info(self.request, _("You have a pending cart in checkout"))
            return redirect(request.META.get('HTTP_REFERER'))

        cart.remove_offer(offer)

        messages.info(self.request, _("Removed item from cart."))

        return redirect('vendor:cart')      # Redirect to cart on success


class AccountInformationView(LoginRequiredMixin, TemplateView):
    template_name = 'vendor/checkout.html'

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        
        invoice = get_purchase_invoice(request.user)

        existing_account_address = Address.objects.filter(profile__user=request.user)

        if existing_account_address:
            # TODO: In future the user will be able to select from multiple saved address
            form = AccountInformationForm(initial={'email': request.user.email}, instance=existing_account_address[0])
        else:
            form = AccountInformationForm(initial={
                                          'first_name': request.user.first_name, 'last_name': request.user.last_name, 'email': request.user.email})
        context['form'] = form

        context['invoice'] = invoice

        clear_session_purchase_data(request)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = AccountInformationForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        account_form = form.save(commit=False)

        invoice = get_purchase_invoice(request.user)
        invoice.status = Invoice.InvoiceStatus.CHECKOUT
        invoice.customer_notes = {'remittance_email': form.cleaned_data['email']}
        existing_account_address = Address.objects.filter(
            profile__user=request.user, name=account_form.name, first_name=account_form.first_name, last_name=account_form.last_name)
        # TODO: Need to add a drop down to select existing address
        if existing_account_address:
            account_form.pk = existing_account_address.first().pk

        account_form.profile = invoice.profile
        account_form.save()
        invoice.shipping_address = account_form
        invoice.save()

        return redirect('vendor:checkout-payment')


class PaymentView(LoginRequiredMixin, TemplateView):
    '''
    Review items and submit Payment
    '''
    template_name = "vendor/checkout.html"

    def get(self, request, *args, **kwargs):
        invoice = get_purchase_invoice(request.user)

        context = super().get_context_data()

        processor = payment_processor(invoice)

        context = processor.get_checkout_context(context=context)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = get_purchase_invoice(request.user)

        credit_card_form = CreditCardForm(request.POST)
        if request.POST.get('same_as_shipping') == 'on':
            billing_address_form = BillingAddressForm(instance=invoice.shipping_address)
            billing_address_form.data = billing_address_form.initial
            billing_address_form.is_bound = True
        else:
            billing_address_form = BillingAddressForm(request.POST)

        if not (billing_address_form.is_valid() and credit_card_form.is_valid()):
            processor = payment_processor(invoice)
            context['billing_address_form'] = billing_address_form
            context['credit_card_form'] = credit_card_form
            return render(request, self.template_name, processor.get_checkout_context(context=context))
        else:
            billing_address_form.full_clean()
            credit_card_form.full_clean()
            request.session['billing_address_form'] = billing_address_form.cleaned_data
            request.session['credit_card_form'] = credit_card_form.cleaned_data
            return redirect('vendor:checkout-review')


class ReviewCheckoutView(LoginRequiredMixin, TemplateView):
    template_name = 'vendor/checkout.html'

    def get(self, request, *args, **kwargs):
        invoice = get_purchase_invoice(request.user)

        context = super().get_context_data()

        processor = payment_processor(invoice)
        if 'billing_address_form' in request.session:
            context['billing_address_form'] = BillingAddressForm(request.session['billing_address_form'])
        if 'credit_card_form' in request.session:
            context['credit_card_form'] = CreditCardForm(request.session['credit_card_form'])
        
        context = processor.get_checkout_context(context=context)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = get_purchase_invoice(request.user)

        processor = payment_processor(invoice)
        
        processor.get_billing_address_form_data(request.session.get('billing_address_form'), BillingAddressForm)
        processor.get_payment_info_form_data(request.session.get('credit_card_form'), CreditCardForm)

        processor.authorize_payment()

        if processor.transaction_submitted:
            for order_item_subscription in [order_item for order_item in processor.invoice.order_items.all() if order_item.offer.terms >= TermType.SUBSCRIPTION and order_item.offer.terms < TermType.ONE_TIME_USE]:
                processor.subscription_payment(order_item_subscription)
            clear_session_purchase_data(request)
            return redirect('vendor:purchase-summary', pk=invoice.pk)
        else:
            messages.info(self.request, _(
                "The payment gateway did not authroize payment."))
            return redirect('vendor:checkout-account')


class PaymentSummaryView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'vendor/payment_summary.html'


class OrderHistoryListView(LoginRequiredMixin, ListView):
    '''
    List of all the invoices generated by the current user on the current site.
    '''
    model = Invoice
    # TODO: filter to only include the current user's order history

    def get_queryset(self):
        try:
            # The profile and user are site specific so this should only return what's on the site for that user excluding the cart
            return self.request.user.customer_profile.get().invoices.filter(status__gt=Invoice.InvoiceStatus.CART)
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
