import urllib.parse
import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from vendor.models import Receipt, Invoice, Payment
from vendor.processors import PaymentProcessor

payment_processor = PaymentProcessor


class AuthorizeNetBaseAPI(View):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        if not self.valid_post():
            raise PermissionDenied()
        return super().dispatch(*args, **kwargs)
    
    def valid_post(self):
        payload_encoded = urllib.parse.urlencode(self.request.POST).encode('utf8')
        hash_value =  hmac.new(settings.AUTHORIZE_NET_SIGNITURA_KEY, payload_encoded, hashlib.sha512).hexdigest()
        
        if hash_value == settings.AUTHORIZE_NET_SIGNITURA_KEY:
            return True

        return False



class AuthroizeCaptureAPI(AuthorizeNetBaseAPI):
    """
    API endpoint to get event notifications from authorizenet when a authcaputre is created.
    If there is a subscription id the endpoint will create a Invoice, Payment and receipt
    to update such subscription. If no subscription id is passed there is nothing to process.
    """
    
    def post(self, request, *args, **kwargs):
        transaction_id = request.POST.get('id')
        dummpy_invoice = Invoice()

        processor = payment_processor(dummy_invoice)
        transaction_detail = processor.get_transaction_detail(transaction_id)

        if 'subscription' not in transaction_detail:
            return JsonResponse({})

        old_receipt = Receipt.objects.get(transaction=transaction_detail['subscription']['id'])

        invoice = Invoice(status=Invoice.InvoiceStatus.PROCESSING, site=old_receipt.order_item.invoice.site)
        invoice.profile = old_receipt.customer_profile
        invoice.save()
        invoice.addOffer(old_receipt.order_item.offer)
        
        processor = PaymentProcessor(invoice)
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