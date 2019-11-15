from django.utils import timezone
from django.db.models import F
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.utils.translation import ugettext as _

from django.views import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView

from vendor.models import Offer, OrderItem, Invoice, Price, Purchase, Refund, CustomerProfile, PurchaseStatus, OrderStatus
from vendor.forms import AddToCartForm, AddToCartModelForm, PaymentForm, RequestRefundForm

import stripe

class NewAddToCartView(CreateView):
    model = OrderItem
    form_class = AddToCartModelForm                                                         # todo: Move to a regular Form from a ModelForm since the advantages of the ModelForm are not used...
    success_url = reverse_lazy('vendor-user-cart-retrieve')

    def form_valid(self, form):

        invoice, invoice_created = self.request.user.invoice_set.get_or_create(status=OrderStatus.CART.value)   # todo: Need to see if there is a way to make sure there is a cart and handle the theoretical case of multiples (thought it should be a 'singleton').

        quantity = form.instance.quantity                                                               # How many?
        offer = Offer.objects.get( sku=self.kwargs['sku'] )                                             # SKU is in the URL...

        order_item, created = invoice.order_items.get_or_create(offer=offer)                            # Get or Create an order item with the matching values

        if not created:                                                                                 # Add the quantity if it already exists
            order_item.quantity += quantity
        else:                                                                                           # Set the value if it does not
            order_item.quantity = quantity

        order_item.save()
        messages.info(self.request, _("Item added to cart."))

        return redirect(self.success_url)


class AddToCartView(LoginRequiredMixin, CreateView):
    model = OrderItem
    form_class = AddToCartModelForm
    success_url = reverse_lazy('vendor-user-cart-retrieve')

    # def get_object(self, queryset=None):
    #     self.offer = self.request.POST.get('offer')         # todo: This is meant to return a model object, not a string...
    #     return self.offer

    def form_valid(self,form):
        # offer = Offer.objects.get(id = self.get_object()) 
        offer = Offer.objects.get(sku=self.request.POST.get('offer') ) 
    
        price = offer.current_price() #sale_price.filter(start_date__lte= timezone.now(), end_date__gte=timezone.now()).order_by('priority').first()

        invoice = Invoice.objects.filter(user = self.request.user, status=OrderStatus.CART.value)

        # check if there is an invoice with status= cart for the user
        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order_items.filter(offer__sku = offer.sku)

            # check if the order_item is there in the invoice, if yes increase the quantity
            if order_item.exists():
                order_item.update(quantity=F('quantity')+1)
                messages.info(self.request, _("Item quantity was updated."))
                return redirect(self.success_url)

            # Create an order_item object for the invoice
            else:
                order_item = self.model.objects.create(
                    invoice = invoice_qs,
                    offer=offer,
                    price=price
                )
                messages.info(self.request, _("Item added to cart."))
                return redirect(self.success_url)

        # Create a invoice object with status = cart
        else:
            ordered_date = timezone.now()
            invoice = Invoice.objects.create(user=self.request.user, ordered_date=ordered_date)

            order_item = OrderItem.objects.create(invoice = invoice, offer = offer, price = price)
            messages.info(self.request, _("Item added to cart."))
            return redirect(self.success_url)


class RemoveFromCartView(LoginRequiredMixin, DeleteView):
    model = OrderItem
    template_name = "vendor/removeitem.html"
    success_url = reverse_lazy('vendor-user-cart-retrieve')

    def get_object(self, queryset=None):
        invoice = Invoice.objects.get(user = self.request.user, status=OrderStatus.CART.value)
        return invoice.order_items.get(offer__sku = self.kwargs['sku'])

    def form_valid(self, form):
        self.get_object().delete()
        messages.info(self.request, _("Item removed from cart"))
        return redirect(self.success_url)


class RetrieveCartView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "vendor/retrievecart.html"

    def get_queryset(self):
        invoice = self.model.objects.filter(user = self.request.user, status=OrderStatus.CART.value).first()
        if invoice:
            return invoice.order_items.all()

        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        count = 0
        invoice = self.model.objects.filter(user = self.request.user, status=OrderStatus.CART.value)
        if invoice:
            context['invoice'] = True

        if self.get_queryset():
            for item in self.get_queryset():
                count += item.quantity

            context['item_count'] = count
        
        return context
        

class DeleteCartView(LoginRequiredMixin, DeleteView):
    model = Invoice

    def delete(request):

        invoice = self.model.filter(user = request.user, status = 0)

        if invoice:
            invoice[0].order_items.all().delete()
            invoice[0].delete()

            messages.info(request, "User Cart deleted.")
            return redirect("vendor:vendor_index")

        else:
            messages.info(request, "You do not have an active cart.")
            return redirect("vendor:vendor_index")


class RetrievePurchasesView(LoginRequiredMixin, ListView):
    model = Purchase
    template_name = "vendor/retrievepurchases.html"

    def get_queryset(self):
        return self.model.objects.filter(user = self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        for item in self.get_queryset():
            if item.status == PurchaseStatus.ACTIVE or item.status == PurchaseStatus.QUEUED:
                context['refund'] = "Request Refund"

            elif item.status == PurchaseStatus.CANCELED:
                context['refund'] = "Refund Requested"

            elif item.status == PurchaseStatus.REFUNDED:
                context['refund'] = "Refund Issued"

            return context

  
class RetrieveOrderSummaryView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "vendor/ordersummary.html"

    def get_queryset(self):
        invoice = self.model.objects.get(user = self.request.user, status=OrderStatus.CART.value)
        return invoice.order_items.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        count = 0
        total = 0
    
        for item in self.get_queryset():
            count +=  item.quantity
            total += item.total()

        context['item_count'] = count
        context['order_total'] = total
        context['amount'] = total * 100
        context['key'] = settings.STRIPE_PUBLISHABLE_KEY
        
        return context


class PaymentProcessingView(LoginRequiredMixin, View):

    def post(self, *args, **kwargs):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        token = self.request.POST['stripeToken']

        invoice = Invoice.objects.get(user = self.request.user, status=OrderStatus.CART.value)

        total = 0
        
        order_items = invoice.order_items.all()

        for item in order_items:
            total += item.total()

        try:
            customer_profile = CustomerProfile.objects.get(user = self.request.user)
        
        except:
            customer_profile = CustomerProfile.objects.create(user = self.request.user, currency = 'usd', attrs = {})
        
        stripe_customer_id = customer_profile.attrs.get('stripe_customer_id', None)

        if stripe_customer_id != '' and stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        stripe_customer_id)

        else:
            customer = stripe.Customer.create(
                email=self.request.user.email,
                card=token
            )
            customer_profile.attrs['stripe_customer_id'] = customer['id']
            customer_profile.save()
     
        charge = stripe.Charge.create(
            amount=int(total * 100),
            currency='usd',
            description='TrainingCamp Charge',      # todo: this need to be set relative to the offer item.
            customer=customer.id,
            metadata={'invoice_id': invoice.id},
        )

        invoice.status = OrderStatus.COMPLETE.value
        invoice.attrs = {'charge': charge.id}
        invoice.save()

        for items in order_items:
            Purchase.objects.create(order_item = items, product = items.offer.product, user = self.request.user)
        
        messages.success(self.request, _("Your order was successful!"))
        return redirect(reverse_lazy('vendor-user-purchases-retrieve'))

       
class RequestRefundView(LoginRequiredMixin, CreateView):
    model = Refund
    form_class = RequestRefundForm
    template_name = "vendor/requestrefund.html"

    def get_object(self, queryset=None):
        self.purchase = Purchase.objects.get(id=self.kwargs['id'])
        return self.purchase

    def form_valid(self,form):

        purchase = self.get_object()

        reason = self.request.POST.get('reason')

        Refund.objects.create(purchase = purchase, reason = reason, user = self.request.user)

        purchase.status = PurchaseStatus.CANCELED.value
        purchase.save()

        messages.info(self.request, _("Refund request created"))
        return redirect(reverse_lazy('vendor-user-purchases-retrieve'))


class RetrieveRefundRequestsView(LoginRequiredMixin, ListView):
    model = Refund 
    template_name = "vendor/refundrequests.html"

    def get_queryset(self):
        return self.model.objects.all()


class IssueRefundView(LoginRequiredMixin, CreateView):
    model = Refund 
    success_url = reverse_lazy('vendor-retrieve-refund-requests')

    def get_queryset(self):
        return self.model.objects.get(id = self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        refund = self.get_queryset()
        purchase = refund.purchase

        invoice = purchase.order_item.invoice 

        charge = invoice.attrs['charge']

        stripe.Refund.create(
            charge=charge, amount = int(purchase.order_item.price.cost * 100))

        refund.accepted = True
        refund.save()

        purchase.status = PurchaseStatus.REFUNDED.value
        purchase.save()

        messages.info(request, _("Refund was issued"))

        return redirect(reverse_lazy('vendor-retrieve-refund-requests'))


class RemoveSingleItemFromCartView(LoginRequiredMixin, UpdateView):

    def update(request, sku):
        offer = get_object_or_404(Offer, sku=sku)

        invoice = Invoice.objects.filter(user = request.user, status=OrderStatus.CART.value)

        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order_items.filter(offer__sku = sku)

            # check if the order_item is there in the invoice, if yes delete the order_item object
            if order_item.exists():
                if order_item[0].quantity > 1:
                    order_item.update(quantity=F('quantity')-1)
                    messages.info(request, _("The quantity of the item reduced from your cart"))

                else:
                    order_item[0].delete()
                    messages.info(request, _("This item removed from your cart"))

                return redirect("vendor:vendor_index")

            else:
                messages.info(request, _("This item was not in your cart."))
                return redirect("vendor:vendor_index")

        else:
            messages.info(request, _("You do not have an active order"))
            return redirect("vendor:vendor_index")


class IncreaseItemQuantityCartView(LoginRequiredMixin, UpdateView):

    def update(request, sku):
        offer = get_object_or_404(Offer, sku=sku)

        invoice = Invoice.objects.filter(user = request.user, status=OrderStatus.CART.value)

        if invoice.exist():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order_items.filter(offer__sku = sku)

            if order_item.exists():
                order_item.update(quantity=F('quantity')+1)
                messages.info(request, "The quantity of the item increased in your cart")

                return redirect("vendor:vendor_index")

            else:
                messages.info(request, "This item was not in your cart.")
                return redirect("vendor:vendor_index")

        else:
            messages.info(request, "You do not have an active order")
            return redirect("vendor:vendor_index")

        



   

  
