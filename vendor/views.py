from django.utils import timezone
from django.db.models import F
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.urls import reverse, reverse_lazy

from django.views import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView

from vendor.models import Offer, OrderItem, Invoice, Price, Purchase
from vendor.forms import AddToCartForm


class VendorIndexView(TemplateView):
    template_name = "vendor/index.html"


class AddToCartView(CreateView):
    model = OrderItem
    form_class = AddToCartForm
    template_name = "vendor/addtocart.html"
    # success_url = reverse_lazy('add_to_cart')

    def get_object(self, queryset=None):
        self.offer = self.request.POST.get('offer')
        return self.offer

    def form_valid(self,form):
        offer = Offer.objects.get(id = self.get_object()) 
    
        price = offer.sale_price.filter(start_date__lte= timezone.now(), end_date__gte=timezone.now()).order_by('priority').first()

        invoice = Invoice.objects.filter(user = self.request.user, status = 0)

        # check if there is an invoice with status= cart for the user
        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order.filter(offer__sku = offer.sku)

            # check if the order_item is there in the invoice, if yes increase the quantity
            if order_item.exists():
                order_item.update(quantity=F('quantity')+1)
                messages.info(self.request, "This item quantity was updated.")
                return redirect(reverse_lazy('vendor-user-cart-retrieve'))

            # Create an order_item object for the invoice
            else:
                order_item = OrderItem.objects.create(
                    invoice = invoice_qs,
                    offer=offer,
                    price=price
                )
                messages.info(self.request, "This item was added to your cart.")
                return redirect(reverse_lazy('vendor-user-cart-retrieve'))

        # Create a invoice object with status = cart
        else:
            ordered_date = timezone.now()
            invoice = Invoice.objects.create(user=self.request.user, ordered_date=ordered_date)

            order_item = OrderItem.objects.create(invoice = invoice, offer = offer, price = price)
            messages.info(self.request, "This item was added to your cart.")
            return redirect(reverse_lazy('vendor-user-cart-retrieve'))


class RemoveFromCartView(DeleteView):
    model = OrderItem
    template_name = "vendor/removeitem.html"
    success_url = reverse_lazy('vendor-user-cart-retrieve')

    def get_object(self, queryset=None):
        invoice = Invoice.objects.get(user = self.request.user, status = 0)
        return invoice.order.get(offer__sku = self.kwargs['sku'])

    def delete(self, request, *args, **kwargs):

        self.get_object().delete()
        messages.info(request, "This item removed from your cart")
        return redirect(reverse_lazy('vendor-user-cart-retrieve'))


class RemoveSingleItemFromCartView(UpdateView):

    def update(request, sku):
        offer = get_object_or_404(Offer, sku=sku)

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order.filter(offer__sku = sku)

            # check if the order_item is there in the invoice, if yes delete the order_item object
            if order_item.exists():
                if order_item[0].quantity > 1:
                    order_item.update(quantity=F('quantity')-1)
                    messages.info(request, "The quantity of the item reduced from your cart")

                else:
                    order_item[0].delete()
                    messages.info(request, "This item removed from your cart")

                return redirect("vendor:vendor_index")

            else:
                messages.info(request, "This item was not in your cart.")
                return redirect("vendor:vendor_index")

        else:
            messages.info(request, "You do not have an active order")
            return redirect("vendor:vendor_index")


class IncreaseItemQuantityCartView(UpdateView):

    def update(request, sku):
        offer = get_object_or_404(Offer, sku=sku)

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice.exist():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order.filter(offer__sku = sku)

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


class RetrieveCartView(ListView):
    model = Invoice
    template_name = "vendor/retrievecart.html"

    def get_queryset(self):
        invoice = self.model.objects.filter(user = self.request.user, status = 0)
        if invoice:
            invoice_qs = invoice[0]
            return invoice_qs.order.all()

        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        count = 0
        invoice = self.model.objects.filter(user = self.request.user, status = 0)
        if invoice:
            context['invoice'] = True

        if self.get_queryset():
            for item in self.get_queryset():
                count += item.quantity

            context['item_count'] = count
        
        return context
        

class DeleteCartView(DeleteView):
    model = Invoice

    def delete(request):

        invoice = self.model.filter(user = request.user, status = 0)

        if invoice:
            invoice[0].order.all().delete()
            invoice[0].delete()

            messages.info(request, "User Cart deleted.")
            return redirect("vendor:vendor_index")

        else:
            messages.info(request, "You do not have an active cart.")
            return redirect("vendor:vendor_index")


class RetrievePurchasesView(ListView):
    model = Purchase

    def get_queryset(self):
        return self.model.objects.filter(user = self.request.user)


class RetrieveOrderSummaryView(ListView):
    model = Invoice
    template_name = "vendor/ordersummary.html"

    def get_queryset(self):
        invoice = self.model.objects.get(user = self.request.user, status = 0)
        return invoice.order.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        count = 0
        total = 0
    
        for item in self.get_queryset():
            count +=  item.quantity
            total += item.total()

        context['item_count'] = count
        context['order_total'] = total
        
        return context
