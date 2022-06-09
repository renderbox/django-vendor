import json
import hashlib
import hmac
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied, MultipleObjectsReturned, ObjectDoesNotExist
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from vendor.models import Receipt, Invoice, Subscription, Payment
from vendor.models.choice import InvoiceStatus, PurchaseStatus
from vendor.processors.authorizenet import AuthorizeNetProcessor
from vendor.utils import get_site_from_request


logger = logging.getLogger(__name__)

payment_processor = AuthorizeNetProcessor


def update_payment(site, transaction_id, json_data):
    try:
        payment = Payment.objects.get(profile__site=site, transaction=transaction_id)
        payment.status = PurchaseStatus.CAPTURED
        payment.result[timezone.now().strftime("%Y-%m-%d_%H:%M:%S")] = json_data
        payment.save()
    
    except MultipleObjectsReturned as exce:
        logger.error(f"AuthorizeCaptureAPI update_payment multiple payments for transaction: {transaction_id} error: {exce}")

    except ObjectDoesNotExist as exce:
        logger.error(f"AuthorizeCaptureAPI update_payment payment does not exist for transaction: {transaction_id} error: {exce}")

    except Exception as exce:
        logger.error(f"AuthorizeCaptureAPI update_payment error: {exce}")
    
def renew_subscription_task(site, json_data, transaction_detail):
    """
    function to be added or called to a task queue to handle the the a subscription renewal.
    """
    transaction_id = json_data['payload']['id']

    payment_info = {
        'account_number': transaction_detail.payment.creditCard.cardNumber.text[-4:],
        'account_type': transaction_detail.payment.creditCard.cardType.text,
        'full_name': " ".join([transaction_detail.billTo.firstName.text, transaction_detail.billTo.lastName.text]),
        'raw': str(json_data),
        'transaction_id': transaction_id,
        'subscription_id': transaction_detail.subscription.id.text,
        'payment_number': transaction_detail.subscription.payNum.text
    }
    
    try:
        subscription = Subscription.objects.get(gateway_id=transaction_detail.subscription.id.text)
    except MultipleObjectsReturned as exce:
        logger.error(f"renew_subscription_task more than one subscription returned, for {transaction_detail.subscription.id.text} exce: {exce}")
        return None
    except ObjectDoesNotExist as exce:
        logger.error(f"renew_subscription_task subscription does not exist {transaction_detail.subscription.id.text} exce: {exce}")
        return None

    try:
        payment = subscription.payments.get(transaction=None, status=PurchaseStatus.QUEUED)
        receipt = subscription.receipts.get(transaction=None)

        payment.transaction = transaction_id
        payment.status = PurchaseStatus.CAPTURED
        payment.result = {}
        payment.result['raw'] = json_data
        payment.save()

        receipt.transaction = transaction_id
        receipt.meta.update(payment.result)
        receipt.save()
        logger.info("renew_subscription_task payment and receipt updated")

    except MultipleObjectsReturned as exce:
        logger.error(f"renew_subscription_task multiple payments returned with None as Transaction, for {transaction_detail.subscription.id.text} exce: {exce}")
        return None

    except ObjectDoesNotExist as exce:
        past_payment = subscription.payments.all().order_by('created').last()
        past_receipt = subscription.receipts.all().order_by('created').last()

        if not (past_payment or past_receipt):
            logger.error(f"renew_subscription_task no past receipt or payments exist for {transaction_detail.subscription.id.text} exce: {exce}")
            return None

        invoice = Invoice.objects.create(
            status=InvoiceStatus.CHECKOUT,
            site=past_payment.profile.site,
            profile=past_payment.profile,
            ordered_date=timezone.now(),
            total=transaction_detail.authAmount.pyval
        )
        invoice.add_offer(past_receipt.order_item.offer)
        invoice.save()

        processor = AuthorizeNetProcessor(site, invoice)
        processor.subscription = subscription
        processor.renew_subscription(past_receipt, payment_info)
        logger.info("renew_subscription_task subscription renewed")


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


class AuthorizeCaptureAPI(AuthorizeNetBaseAPI):
    """
    API endpoint to get event notifications from authorizenet when a authcaputre is created.
    If there is a subscription tied to the transaction, it will renew such subscription
    """

    def post(self, request, *args, **kwargs):
        logger.info(f"AuthorizeNet AuthCapture Event webhook: {request.POST}")
        site = get_site_from_request(request)

        if not request.body:
            logger.warning("Webhook event has no body")
            return JsonResponse({"msg": "Invalid request body."})

        if not self.is_valid_post():
            logger.error(f"authcapture: Request was denied: {request}")
            raise PermissionDenied()

        request_data = json.loads(request.body)
        transaction_id = request_data['id']
        logger.info(f"renew_subscription_task Getting transaction detail for id: {transaction_id}")
        
        processor = payment_processor(site)
        transaction_detail = processor.get_transaction_detail(transaction_id)

        if not hasattr(transaction_detail, 'subscription'):
            update_payment(site, transaction_id, request_data)
        else:
            renew_subscription_task(site, request_data, transaction_detail)

        return JsonResponse({"msg": "AuthorizeCaptureAPI finished"})
