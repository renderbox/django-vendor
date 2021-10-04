import json
import hashlib
import hmac
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from vendor.models import Receipt, Invoice
from vendor.processors.authorizenet import AuthorizeNetProcessor

logger = logging.getLogger(__name__)

payment_processor = AuthorizeNetProcessor


def renew_subscription_task(json_data):
    """
    function to be added or called to a task queue to handle the the a subscription renewal.
    """
    transaction_id = json_data['payload']['id']
    dummy_invoice = Invoice()

    processor = payment_processor(dummy_invoice)
    logger.info(f"Getting transaction detail for id: {transaction_id}")
    transaction_detail = processor.get_transaction_detail(transaction_id)

    if not hasattr(transaction_detail, 'subscription'):
        return None
    if transaction_detail.subscription.payNum.pyval == 1:
        return None

    past_receipt = Receipt.objects.filter(transaction=transaction_detail.subscription.id.text).order_by('created').last()

    payment_info = {
        'account_number': transaction_detail.payment.creditCard.cardNumber.text[-4:],
        'account_type': transaction_detail.payment.creditCard.cardType.text,
        'full_name': " ".join([transaction_detail.billTo.firstName.text, transaction_detail.billTo.lastName.text]),
        'raw': str(json_data),
        'transaction_id': transaction_id,
        'subscription_id': transaction_detail.subscription.id.text,
        'payment_number': transaction_detail.subscription.payNum.text
    }

    invoice_history = []

    for receipt in Receipt.objects.filter(transaction=transaction_detail.subscription.id.text).order_by('created'):
        past_invoice = receipt.order_item.invoice
        invoice_info = {
            "invoice_id": past_invoice.pk,
            "receipt_id": receipt.pk,
            "payments": [payment.pk for payment in past_invoice.payments.all()]
        }
        invoice_history.append(invoice_info)

    invoice = Invoice(status=Invoice.InvoiceStatus.PROCESSING, site=past_receipt.order_item.invoice.site)
    invoice.profile = past_receipt.profile
    invoice.ordered_date = timezone.now()
    invoice.vendor_notes['history'] = invoice_history
    invoice.save()
    invoice.add_offer(past_receipt.order_item.offer)
    invoice.total = transaction_detail.authAmount.pyval
    invoice.save()

    processor = AuthorizeNetProcessor(invoice)
    processor.renew_subscription(past_receipt, payment_info)


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
        logger.info(f"Request body: {self.request.body}")
        logger.info(f"X ANET SIGNATURE: {self.request.META.get('HTTP_X_ANET_SIGNATURE')}")

        if 'HTTP_X_ANET_SIGNATURE' not in self.request.META:
            logger.warning("Webhook warning Signature KEY")
            return False

        hash_value = hmac.new(bytes(settings.AUTHORIZE_NET_SIGNATURE_KEY, 'utf-8'), self.request.body, hashlib.sha512).hexdigest()
        logger.info(f"Checking hashs\nCALCULATED: {hash_value}\nREQUEST VALUE: {self.request.META.get('HTTP_X_ANET_SIGNATURE')[7:]}")
        if hash_value.upper() == self.request.META.get('HTTP_X_ANET_SIGNATURE')[7:]:
            return True

        return False


class AuthroizeCaptureAPI(AuthorizeNetBaseAPI):
    """
    API endpoint to get event notifications from authorizenet when a authcaputre is created.
    If there is a subscription tied to the transaction, it will renew such subscription
    """

    def post(self, request, *args, **kwargs):
        logger.info(f"AuthorizeNet AuthCapture Event webhook: {request.POST}")

        if not request.body:
            logger.warning("Webhook event has no body")
            return JsonResponse({"msg": "Invalid request body."})

        if not self.is_valid_post():
            logger.error(f"authcapture: Request was denied: {request}")
            # raise PermissionDenied() # This will be uncommented out until we know that a valid call is being properly validated. 

        request_data = json.loads(request.body)
        logger.info(f"Renewing subscription request body: {request_data}")
        renew_subscription_task(request_data)
        logger.info("authcapture subscription renewed")

        return JsonResponse({"msg": "subscription renewed"})
