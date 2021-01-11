from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.utils import timezone

from vendor.models import Receipt, Invoice, Payment
from vendor.processors import PaymentProcessor

payment_processor = PaymentProcessor

class AuthroizeCaptureAPI(View):
    """
    API endpoint to get event notifications from authorizenet when a authcaputre is created.
    If there is a subscription id the endpoint will create a Invoice, Payment and receipt
    to update such subscription. If no subscription id is passed there is nothing to process.
    """
    def post(self, request, *args, **kwargs):
        if 'subscription' not in kwargs:
            return JsonResponse({})
        old_receipt = Receipt.objects.get(transaction=kwargs.get('id'))

        invoice = Invoice(status=Invoice.InvoiceStatus.PROCESSING, site=old_receipt.order_item.invoice.site)
        invoice.profile = old_receipt.customer_profile
        invoice.save()
        invoice.addOffer(old_receipt.order_item.offer)


        processor = payment_processor(invoice)

        processor.renew_subscription(old_receipt.transaction)

        # payment = Payment()
        # payment.transaction = old_receipt.transaction
        # payment.invoice = invoice
        # payment.provider = 'TODO:'
        # payment.amount = invoice.total
        # payment.billing_address = Payment.objects.get(transaction=old_receipt.transaction).values_list('billing_address')
        # payment.result['raw'] = str({**kwargs, **(kwargs.__dict__)})
        # payment.success = True
        # payment.payee_full_name = 'todo'
        # payment.save()

        # new_receipt = Receipt()
        # new_receipt = old_receipt.profile
        # new_receipt.order_item = old_receipt.order_item
        # new_receipt.start_date = timezone.now()
        # new_receipt.end_date = 'todo'
        # new_receipt.transaction = old_receipt.transaction
        # new_receipt.status = old_receipt.status
        # new_receipt.save

        return JsonResponse({})