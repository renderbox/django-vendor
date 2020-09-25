from django.utils import timezone
from django.db.models import F
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist

from django.views import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.http import HttpResponse
from vendor.models import Offer, OrderItem, Invoice, Payment, Address
from vendor.models.address import Address as GoogleAddress
from vendor.models.choice import TermType
from vendor.models.utils import set_default_site_id
from vendor.processors import PaymentProcessor
from vendor.forms import BillingAddressForm, CreditCardForm, AccountValidationForm


# The Payment Processor configured in settings.py
payment_processor = PaymentProcessor


class CartView(LoginRequiredMixin, DetailView):
    '''
    View items in the cart
    '''
    model = Invoice

    def get_object(self):
        profile, created = self.request.user.customer_profile.get_or_create(
            site=set_default_site_id())
        return profile.get_cart()


class AddToCartView(LoginRequiredMixin, TemplateView):
    '''
    Create an order item and add it to the order
    '''

    def get(self, *args, **kwargs):         # TODO: Move to POST
        offer = Offer.objects.get(slug=self.kwargs["slug"])
        profile, created = self.request.user.customer_profile.get_or_create(
            site=set_default_site_id())

        cart = profile.get_cart()
        cart.add_offer(offer)

        messages.info(self.request, _("Added item to cart."))

        return redirect('vendor:cart')      # Redirect to cart on success


class RemoveFromCartView(LoginRequiredMixin, DeleteView):
    '''
    Reduce the count of items from the cart and delete the order item if you reach 0
    TODO: Change to form/POST for better security & flexibility
    '''

    def get(self, *args, **kwargs):         # TODO: Move to POST
        offer = Offer.objects.get(slug=self.kwargs["slug"])

        profile = self.request.user.customer_profile.get(
            site=settings.SITE_ID)      # Make sure they have a cart
        cart = profile.get_cart()
        cart.remove_offer(offer)

        messages.info(self.request, _("Removed item from cart."))

        return redirect('vendor:cart')      # Redirect to cart on success


class AccountValidationView(LoginRequiredMixin, FormView):
    form_class = AccountValidationForm
    template_name = 'vendor/checkout.html'

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.customer_profile.get(site=settings.SITE_ID)
        invoice = profile.invoices.get(status=Invoice.InvoiceStatus.CART)

        context['invoice'] = Invoice.objects.get(uuid=kwargs.get('uuid'))

        if 'billing_address_form' in request.session:
            del(request.session['billing_address_form'])
        if 'credit_card_form' in request.session:
            del(request.session['credit_card_form'])

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user_form = self.form_class(request.POST)
        logged_user = self.request.user
        if not user_form.is_valid():
            return render(request, self.template_name, {'form': user_form})

        user_account = user_form.save(commit=False)
        if user_account.first_name == logged_user.first_name and user_account.last_name == logged_user.last_name and user_account.email == logged_user.email:
            return redirect('vendor:checkout-payment', uuid=kwargs.get('uuid'))
        else:
            messages.info(self.request, _("Invalid Account"))
            return redirect('vendor:checkout-account', uuid=kwargs.get('uuid'))


class CheckoutView(LoginRequiredMixin, TemplateView):
    '''
    Review items and submit Payment
    '''
    template_name = "vendor/checkout.html"

    def get(self, request, *args, **kwargs):
        invoice = Invoice.objects.get(uuid=kwargs.pop('uuid'))

        context = super().get_context_data()

        processor = payment_processor(invoice)

        context = processor.get_checkout_context(context=context)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = Invoice.objects.get(uuid=kwargs.get('uuid'))

        credit_card_form = CreditCardForm(request.POST)
        billing_address_form = BillingAddressForm(request.POST)

        processor = payment_processor(invoice)
        if not (billing_address_form.is_valid() and credit_card_form.is_valid()):
            context['billing_address_form'] = billing_address_form
            context['credit_card_form'] = credit_card_form
            return render(request, self.template_name, processor.get_checkout_context(context=context))
        else:
            billing_address_form.full_clean()
            credit_card_form.full_clean()
            request.session['billing_address_form'] = billing_address_form.cleaned_data
            request.session['credit_card_form'] = credit_card_form.cleaned_data
            return redirect('vendor:checkout-review', uuid=kwargs.get('uuid'))


class ReviewCheckout(LoginRequiredMixin, TemplateView):
    template_name = 'vendor/checkout.html'

    def get(self, request, *args, **kwargs):
        invoice = Invoice.objects.get(uuid=kwargs.pop('uuid'))

        context = super().get_context_data()

        processor = payment_processor(invoice)

        context = processor.get_checkout_context(context=context)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = Invoice.objects.get(uuid=kwargs.get('uuid'))

        processor = payment_processor(invoice)

        processor.process_payment(request)

        if processor.transaction_submitted:
            for order_item_subscription in [order_item for order_item in processor.invoice.order_items.all() if order_item.offer.terms == TermType.SUBSCRIPTION]:
                processor.process_subscription(
                    request, order_item_subscription)
            del(request.session['billing_address_form'])
            del(request.session['credit_card_form'])
            return redirect('vendor:purchase-summary', pk=invoice.pk)
        else:
            messages.info(self.request, _(
                "The payment gateway did not authroize payment."))
            return redirect('vendor:checkout-account', uuid=kwargs.get('uuid'))


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
