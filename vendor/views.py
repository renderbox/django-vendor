from datetime import datetime
from django.utils import timezone

from django.views import View
from django.views.generic import TemplateView

from vendor.models import Offer, OrderItem, Invoice, Price, Purchases


class VendorIndexView(TemplateView):
    template_name = "vendor/index.html"


# class AddToCartView(View):
#
#     def post(self, request, sku):
#         offer = get_object_or_404(Offer, sku=sku)
#
#         price = offer.sale_price.filter(end_date__gte= datetime.now()).order_by('priority')[0]
#
#         invoice = Invoice.objects.filter(user = request.user, status = 0)
#
#         if invoice.exists():
#
#             invoice_qs = invoice[0]
#
#             order_item = invoice_qs.order.filter(offer__sku = sku)
#
#             # check if the order_item is there in the invoice, if yes increase the quantity
#             if order_item.exists():
#                 order_item[0].quantity +=1
#                 order_item[0].save()
#                 messages.info(request, "This item quantity was updated.")
#                 return redirect("vendor:vendor_index")
#
#             else:
#                 order_item = OrderItem.objects.create(
#                     invoice = invoice_qs,
#                     offer=offer,
#                     price=price
#                 )
#                 messages.info(request, "This item was added to your cart.")
#                 return redirect("vendor:vendor_index")
#
#         else:
#             ordered_date = timezone.now()
#             invoice = Invoice.objects.create(user=request.user, ordered_date=ordered_date)
#
#             order_item = OrderItem.objects.create(invoice = invoice, offer = offer, price = price)
#             messages.info(request, "This item was added to your cart.")
#             return redirect("vendor:vendor_index")
#
#
# class RemoveFromCartView(View):
#
#     def update(request, sku):
#         offer = get_object_or_404(Offer, sku=sku)
#
#         invoice = Invoice.objects.filter(user = request.user, status = 0)
#
#         if invoice.exists():
#
#             invoice_qs = invoice[0]
#
#             order_item = invoice_qs.order.filter(offer__sku = sku)
#
#             # check if the order_item is there in the invoice, if yes delete the order_item object
#             if order_item.exists():
#                 order_item[0].delete()
#                 messages.info(request, "This item removed from your cart")
#                 return redirect("vendor:vendor_index")
#
#             else:
#                 messages.info(request, "This item was not in your cart.")
#                 return redirect("vendor:vendor_index")
#
#         else:
#             messages.info(request, "You do not have an active order")
#             return redirect("vendor:vendor_index")
#
#
# class RemoveSingleItemFromCartView(View):
#
#     def update(request, sku):
#         offer = get_object_or_404(Offer, sku=sku)
#
#         invoice = Invoice.objects.filter(user = request.user, status = 0)
#
#         if invoice.exists():
#
#             invoice_qs = invoice[0]
#
#             order_item = invoice_qs.order.filter(offer__sku = sku)
#
#             # check if the order_item is there in the invoice, if yes delete the order_item object
#             if order_item.exists():
#                 if order_item[0].quantity > 1:
#                     order_item[0].quantity -=1
#                     order_item[0].save()
#                     messages.info(request, "The quantity of the item reduced from your cart")
#
#                 else:
#                     order_item[0].delete()
#                     messages.info(request, "This item removed from your cart")
#
#                 return redirect("vendor:vendor_index")
#
#             else:
#                 messages.info(request, "This item was not in your cart.")
#                 return redirect("vendor:vendor_index")
#
#         else:
#             messages.info(request, "You do not have an active order")
#             return redirect("vendor:vendor_index")
