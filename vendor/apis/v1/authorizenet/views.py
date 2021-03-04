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
        return super().dispatch(*args, **kwargs)
    
    def is_valid_post(self):
        hash_value = hmac.new(bytes(settings.AUTHORIZE_NET_SIGNITURE_KEY, 'utf-8'), self.request.body, hashlib.sha512).hexdigest()
        
        if hash_value == self.request.META.get('HTTP_X_ANET_SIGNATURE')[7:]:
            return True

        return False

def renew_subscription_task(json_data):
    """
    function to be added or called to a task queue to handle the the a subscription renewal.
    """
    transaction_id = json_data['payload']['id']
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
        'raw': str({**json_data, **(json_data.__dict__)})}
    

    invoice = Invoice(status=Invoice.InvoiceStatus.PROCESSING, site=past_receipt.order_item.invoice.site)
    invoice.profile = past_receipt.profile
    invoice.save()
    invoice.add_offer(past_receipt.order_item.offer)
    
    processor = PaymentProcessor(invoice)
    processor.renew_subscription(past_receipt, payment_info)

class AuthroizeCaptureAPI(AuthorizeNetBaseAPI):
    """
    API endpoint to get event notifications from authorizenet when a authcaputre is created.
    If there is a subscription tied to the transaction, it will renew such subscription
    """
    
    def post(self, request, *args, **kwargs):
        if self.is_valid_post():
            raise PermissionDenied()

        renew_subscription_task(json.loads(request.body))

        return JsonResponse({})