from django.utils import timezone
from django.db.models import F

from django.views import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView

from vendor.models import Offer, OrderItem, Invoice, Price, Purchase


class VendorIndexView(TemplateView):
    template_name = "vendor/index.html"


class AddToCartView(CreateView):

    def post(self, request, sku):
        offer = get_object_or_404(Offer, sku=sku)

        price = offer.sale_price.filter(start_date__lte= timezone.now(), end_date__gte=timezone.now()).order_by('priority').first()

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        # check if there is an invoice with status= cart for the user
        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order.filter(offer__sku = sku)

            # check if the order_item is there in the invoice, if yes increase the quantity
            if order_item.exists():
                order_item[0].quantity +=1
                order_item[0].save()
                messages.info(request, "This item quantity was updated.")
                return redirect("vendor:vendor_index")

            else:
                order_item = OrderItem.objects.create(
                    invoice = invoice_qs,
                    offer=offer,
                    price=price
                )
                messages.info(request, "This item was added to your cart.")
                return redirect("vendor:vendor_index")

        else:
            ordered_date = timezone.now()
            invoice = Invoice.objects.create(user=request.user, ordered_date=ordered_date)

            order_item = OrderItem.objects.create(invoice = invoice, offer = offer, price = price)
            messages.info(request, "This item was added to your cart.")
            return redirect("vendor:vendor_index")


class RemoveFromCartView(UpdateView):

    def update(request, sku):
        offer = get_object_or_404(Offer, sku=sku)

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order.filter(offer__sku = sku)

            # check if the order_item is there in the invoice, if yes delete the order_item object
            if order_item.exists():
                order_item[0].delete()
                messages.info(request, "This item removed from your cart")
                return redirect("vendor:vendor_index")

            else:
                messages.info(request, "This item was not in your cart.")
                return redirect("vendor:vendor_index")

        else:
            messages.info(request, "You do not have an active order")
            return redirect("vendor:vendor_index")


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


class RetrieveCartView(DetailView):
    model = Invoice

    def get_queryset(self):
        invoice =  self.model.objects.get(user = self.request.user, status = 0)
        return invoice

    def get_context_data(self, **kwargs):
        context['item_count'] = self.get_queryset().order.all().count()
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
