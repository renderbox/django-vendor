from django.utils import timezone
from django.db.models import F

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from vendor.models import Offer, Price, Invoice, OrderItem, Purchase

# from vendor.models import SampleModel
# from vendor.api.serializers import SampleModelSerializer


# class SampleModelListAPIView(generics.ListAPIView):
#     queryset = SampleModel.objects.filter(enabled=True)
#     serializer_class = SampleModelSerializer


class AddToCartAPIView(APIView):

    def post(self, request, sku, *args, **kwargs):
        offer = Offer.objects.get(sku = sku)

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        price = offer.sale_price.filter(start_date__lte= timezone.now(), end_date__gte=timezone.now()).order_by('priority').first()

        # check if there is an invoice with status= cart for the user
        if invoice.exists():
            invoice_qs = invoice[0]
            order_item = invoice_qs.order.filter(offer__sku = sku)

            # check if the order_item is there in the invoice, if yes increase the quantity
            if order_item.exists():
                order_item.update(quantity=F('quantity')+1)
                return Response(status=status.HTTP_200_OK)

            else:
                order_item = OrderItem.objects.create(
                    invoice = invoice_qs,
                    offer=offer,
                    price=price
                )
                return Response(status=status.HTTP_200_OK)

        else:
            ordered_date = timezone.now()
            invoice = Invoice.objects.create(user=request.user, ordered_date=ordered_date)

            order_item = OrderItem.objects.create(invoice = invoice, offer = offer, price = price)
            return Response(status=status.HTTP_200_OK)


class IncreaseItemQuantityCartAPIView(APIView):

    def patch(self, request, sku, *args, **kwargs):
        offer = Offer.objects.get(sku = sku)

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order.filter(offer__sku = sku)

            # check if the order_item is there in the invoice, if yes decrease the quantity of order_item object
            if order_item.exists():
                order_item.update(quantity=F('quantity')+1)
                return Response(status=status.HTTP_200_OK)

            else:
                return Response(status=status.HTTP_404_NOT_FOUND)

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class RemoveSingleItemFromCartAPIView(APIView):

    def patch(self, request, sku, *args, **kwargs):
        offer = Offer.objects.get(sku = sku)

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order.filter(offer__sku = sku)

            # check if the order_item is there in the invoice, if yes decrease the quantity of order_item object
            if order_item.exists():
                if order_item[0].quantity > 1:
                    order_item.update(quantity=F('quantity')-1)

                else:
                    order_item[0].delete()

                return Response(status=status.HTTP_200_OK)

            else:
                return Response(status=status.HTTP_404_NOT_FOUND)

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class RemoveFromCartAPIView(APIView):

    def patch(self, request, sku, *args, **kwargs):
        offer = Offer.objects.get(sku = sku)

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice.exists():

            invoice_qs = invoice[0]

            order_item = invoice_qs.order.filter(offer__sku = sku)

            # check if the order_item is there in the invoice, if yes delete the order_item object
            if order_item.exists():
                order_item[0].delete()
                return Response(status=status.HTTP_200_OK)

            else:
                return Response(status=status.HTTP_404_NOT_FOUND)

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class RetrieveCartAPIView(APIView):

    def get(self, request, *args, **kwargs):

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice.exists():
            data = {}
            total = 0

            data['username'] = request.user.username

            invoice_qs = invoice[0]

            order_items = invoice_qs.order.all()

            data['order_items'] = []

            for items in order_items:
                item = {}
                item['sku'] = items.offer.sku
                item['name'] = items.offer.product.name
                item['price'] = items.price.cost
                item['quantity'] = items.quantity

                data['order_items'].append(item)

            data['item_count'] = order_items.count()

            return Response(data, status=status.HTTP_200_OK)

        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class DeleteCartAPIView(APIView):

    def delete(self, request, *args, **kwargs):

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice:
            invoice[0].order.all().delete()
            invoice[0].delete()

            return Response(status = status.HTTP_200_OK)

        else:
            return Response(status = status.HTTP_400_BAD_REQUEST)


class RetrievePurchasesAPIView(APIView):

    def get(self, request, *args, **kwargs):

        purchases = Purchase.objects.filter(user = request.user)

        purchase_list = []

        for items in purchases:
            data = {}
            data['sku'] = items.order_item.offer.sku
            data['name'] = items.order_item.offer.name
            data['price'] = items.order_item.price.cost
            data['quantity'] = items.order_item.quantity
            data['start_date'] = items.start_date
            data['end_date'] = items.end_date
            data['status'] = items.status

            purchase_list.append(data)

        return Response(purchase_list, status = status.HTTP_200_OK)


class RetrieveOrderSummaryAPIView(APIView):

    def get(self, request, *args, **kwargs):

        invoice = Invoice.objects.filter(user = request.user, status = 0)

        if invoice.exists():
            data = {}
            total = 0

            data['username'] = request.user.username

            invoice_qs = invoice[0]

            order_items = invoice_qs.order.all()

            data['order_items'] = []

            for items in order_items:
                item = {}
                item['sku'] = items.offer.sku
                item['name'] = items.offer.product.name
                item['price'] = items.price.cost
                item['item_total'] = items.total()
                item['quantity'] = items.quantity

                data['order_items'].append(item)

                total += item['item_total']

            data['total'] = total

            return Response(data, status=status.HTTP_200_OK)

        else:
            return Response(status=status.HTTP_404_NOT_FOUND)
