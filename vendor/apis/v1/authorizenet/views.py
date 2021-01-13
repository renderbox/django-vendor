import json
import hashlib
import hmac
import urllib.parse

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse, QueryDict
from django.views import View
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from vendor.models import Receipt, Invoice, Payment
from vendor.processors import PaymentProcessor

payment_processor = PaymentProcessor


class AuthorizeNetBaseAPI(View):
    """
    Base class to handel Authroize.Net webhooks.
    """

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        """
        Dispatch override to accept post entries without csfr given that they include
        a X-Anet-Signature in there header that must be encoded with Signature Key using
        HMAC-sha512 on the payload.
        Reference: https://developer.authorize.net/api/reference/features/webhooks.html
        """
        if self.request.POST and not self.is_valid_post():
            raise PermissionDenied()
        return super().dispatch(*args, **kwargs)
    
    def is_valid_post(self):
        payload_encoded = urllib.parse.urlencode(self.request.POST).encode('utf8')
        hash_value =  hmac.new(bytes(settings.AUTHORIZE_NET_SIGNITURE_KEY, 'utf-8'), payload_encoded, hashlib.sha512).hexdigest()
        
        if hash_value == self.request.META.get('X-Anet-Signature'):
            return True

        return False


class AuthroizeCaptureAPI(AuthorizeNetBaseAPI):
    """
    API endpoint to get event notifications from authorizenet when a authcaputre is created.
    If there is a subscription tied to the transaction, it will renew such subscription
    """
    
    def post(self, request, *args, **kwargs):
        if isinstance(request.POST.get('payload'), dict):
            payload = request.POST.get('payload')
        else:
            payload = json.loads(request.POST.get('payload'))
        transaction_id = payload['id']
        dummy_invoice = Invoice()

        processor = payment_processor(dummy_invoice)
        transaction_detail = processor.get_transaction_detail(transaction_id)


        if not hasattr(transaction_detail, 'subscription'):
            return JsonResponse({})

        past_receipt = Receipt.objects.filter(transaction=transaction_detail.subscription.id.text).order_by('created').first()

        payment_info = {
            'account_number': transaction_detail.payment.creditCard.cardNumber.text[-4:],
            'account_type': transaction_detail.payment.creditCard.cardType.text,
            'full_name': " ".join([transaction_detail.billTo.firstName.text,transaction_detail.billTo.lastName.text]),
            'raw': str({**request.POST, **(request.POST.__dict__)})}
        

        invoice = Invoice(status=Invoice.InvoiceStatus.PROCESSING, site=past_receipt.order_item.invoice.site)
        invoice.profile = past_receipt.profile
        invoice.save()
        invoice.add_offer(past_receipt.order_item.offer)
        
        processor = PaymentProcessor(invoice)
        processor.renew_subscription(past_receipt, payment_info)

        return JsonResponse({})