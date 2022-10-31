import json
import hashlib
import hmac
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied, MultipleObjectsReturned, ObjectDoesNotExist
from django.http import JsonResponse, HttpResponseRedirect
from django.views import View
from django.views.generic.edit import FormMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.urls import reverse_lazy

from vendor.forms import DateTimeRangeForm
from vendor.integrations import AuthorizeNetIntegration
from vendor.models import Receipt, Invoice, Subscription, Payment
from vendor.models.choice import InvoiceStatus, PurchaseStatus
from vendor.processors.authorizenet import AuthorizeNetProcessor, sync_subscriptions
from vendor.utils import get_site_from_request

logger = logging.getLogger(__name__)


def update_payment(site, transaction_id, transaction_detail):
    processor = AuthorizeNetProcessor(site)

    submitted_datetime = datetime.strptime(transaction_detail.submitTimeUTC.pyval, '%Y-%m-%dT%H:%M:%S.%f%z')
    payment_info = processor.get_payment_info(transaction_detail)
    payment_status = processor.get_payment_status(transaction_detail.transactionStatus.text)
    payment_success = processor.get_payment_success(transaction_detail.responseCode.text)

    try:
        payment = Payment.objects.get(profile__site=site, transaction=transaction_id, status__lt=PurchaseStatus.VOID)
        payment.submitted_date = submitted_datetime
        payment.result[timezone.now().strftime("%Y-%m-%d_%H:%M:%S")] = payment_info
        payment.status = payment_status
        payment.success = payment_success
        payment.save()
    except MultipleObjectsReturned as exce:
        logger.error(f"AuthorizeCaptureAPI update_payment multiple payments for transaction: {transaction_id} error: {exce}")

    except ObjectDoesNotExist as exce:
        logger.error(f"AuthorizeCaptureAPI update_payment payment does not exist for transaction: {transaction_id} error: {exce}")

    except Exception as exce:
        logger.error(f"AuthorizeCaptureAPI update_payment error: {exce}")
        
def subscription_save_transaction(site, transaction_id, transaction_detail):
    processor = AuthorizeNetProcessor(site)

    subscription_id = transaction_detail.subscription.id.text
    logger.info(f"AuthorizeCaptureAPI subscription_save_transaction saving subscription transaction: {transaction_id} for subscription {subscription_id}")

    submitted_datetime = datetime.strptime(transaction_detail.submitTimeUTC.pyval, '%Y-%m-%dT%H:%M:%S.%f%z')
    payment_info = processor.get_payment_info(transaction_detail)
    payment_status = processor.get_payment_status(transaction_detail.transactionStatus.text)
    payment_success = processor.get_payment_success(transaction_detail.responseCode.text)

    try:
        subscription = Subscription.objects.get(gateway_id=subscription_id, profile__site=site)

    except MultipleObjectsReturned as exce:
        logger.error(f"AuthorizeCaptureAPI subscription_save_transaction multiple subscription for id: {subscription_id} error: {exce}")
        subscription = Subscription.objects.filter(gateway_id=subscription_id, profile__site=site).first()

    except ObjectDoesNotExist as exce:
        logger.error(f"subscription_save_transaction subscription does not exist {subscription_id} exce: {exce}")
        return None

    try:
        payment = subscription.payments.get(transaction=None, status=PurchaseStatus.QUEUED)
        payment.transaction = transaction_id
        payment.submitted_date = submitted_datetime
        payment.result[timezone.now().strftime("%Y-%m-%d_%H:%M:%S")] = payment_info
        payment.status = payment_status
        payment.success = payment_success
        payment.save()
        logger.info(f"AuthorizeCaptureAPI subscription_save_transaction: payment {payment.pk} updated")
        
        if payment_status == PurchaseStatus.SETTLED:
            processor = AuthorizeNetProcessor(site, payment.invoice)
            processor.payment = payment
            processor.create_receipts(payment.invoice.order_items.all())
            logger.info(f"AuthorizeCaptureAPI subscription_save_transaction: subscription renewed {subscription.pk}")

    except MultipleObjectsReturned as exce:
        # There should be none or only one payment with transaction None and status in Queue
        logger.error(f"AuthorizeCaptureAPI subscription_save_transaction multiple payments returned with None as Transaction, for {subscription_id} exce: {exce}")
        return None

    except ObjectDoesNotExist as exce:
        logger.info(f"AuthorizeCaptureAPI renew_subscription_task subscription {subscription.pk} renewed")
        invoice = Invoice.objects.create(
            profile=customer_profile,
            site=site,
            ordered_date=submitted_datetime,
            total=transaction_detail.settleAmount.pyval,
            status=InvoiceStatus.COMPLETE
        )
        invoice.add_offer(offer)
        invoice.save()

        processor = AuthorizeNetProcessor(site, invoice)
        processor.subscription = subscription
        
        processor.renew_subscription(subscription, transaction_id, payment_status, payment_success)
        logger.info(f"AuthorizeCaptureAPI subscription_save_transaction creating new payment and receipt for subscription, for {subscription_id}")
        
        return None # No need to continue to create receipt as it is done in the above function

def settle_authorizenet_transactions(site, start_date, end_date):
    processor = AuthorizeNetProcessor(site)

    settled_transactions = processor.get_settled_transactions(start_date, end_date)
    processor.update_payments_to_settled(site, settled_transactions)


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

    def is_valid_post(self, site):
        logger.info(f"AuthorizeNetBaseAPI is_valid_post: Request body: {self.request.body}")
        logger.info(f"AuthorizeNetBaseAPI is_valid_post: X ANET SIGNATURE: {self.request.META.get('HTTP_X_ANET_SIGNATURE')}")

        if 'HTTP_X_ANET_SIGNATURE' not in self.request.META:
            logger.warning("AuthorizeNetBaseAPI is_valid_post: Signature Key not it request")
            return False

        try:
            credentials = AuthorizeNetIntegration(site)

            if credentials.instance and credentials.instance.private_key:
                hash_value = hmac.new(bytes(credentials.instance.private_key, 'utf-8'), self.request.body, hashlib.sha512).hexdigest()
            elif settings.AUTHORIZE_NET_SIGNATURE_KEY:
                hash_value = hmac.new(bytes(settings.AUTHORIZE_NET_SIGNATURE_KEY, 'utf-8'), self.request.body, hashlib.sha512).hexdigest()
            else:
                raise TypeError("No private key set")

            logger.info(f"AuthorizeNetBaseAPI is_valid_post: Checking hashs\nCALCULATED: {hash_value}\nREQUEST VALUE: {self.request.META.get('HTTP_X_ANET_SIGNATURE')[7:]}")

            if hash_value.upper() == self.request.META.get('HTTP_X_ANET_SIGNATURE')[7:]:
                return True

        except TypeError as exce:
            logger.error(f'AuthorizeNetBaseAPI is_valid_post: TypeError Exception: {exce}')

        return False


class AuthorizeCaptureAPI(AuthorizeNetBaseAPI):
    """
    API endpoint to get event notifications from authorizenet when a authcaputre is created.
    If there is a subscription tied to the transaction, it will renew such subscription
    """
    def is_request_valid(self, site, request_data):
        if not request_data:
            logger.warning("AuthorizeCaptureAPI post: Webhook event has no body")
            return False

        if not request_data.get('payload', {}).get('id'):
            logger.error(f"AuthorizeCaptureAPI post: No transaction id request data: {request_data}")
            return False
            
        if not self.is_valid_post(site):
            logger.error(f"AuthorizeCaptureAPI post: Request was denied: {self.request}")
            return False

            
        return True

    def post(self, *args, **kwargs):
        logger.info(f"AuthorizeCaptureAPI post: Event webhook: {self.request.body}")

        site = get_site_from_request(self.request)
        logger.info(f"AuthorizeCaptureAPI post: site: {site}")

        request_data = json.loads(self.request.body)
        logger.info(f"AuthorizeCaptureAPI post: request data: {request_data}")

        if not self.is_request_valid(site, request_data):
            return JsonResponse({"msg": "AuthorizeCaptureAPI post: Request is invalid"})

        transaction_id = request_data.get('payload').get('id')
        logger.info(f"AuthorizeCaptureAPI post: Getting transaction detail for id: {transaction_id}")

        processor = AuthorizeNetProcessor(site)
        transaction_detail = processor.get_transaction_detail(transaction_id)

        if not hasattr(transaction_detail, 'subscription'):
            logger.info(f"AuthorizeCaptureAPI post: updating payment for transaction detail: {transaction_detail}")
            update_payment(site, transaction_id, transaction_detail)

        else:
            logger.info(f"AuthorizeCaptureAPI post: saving subscription transaction: {transaction_detail}")
            subscription_save_transaction(site, request_data.get('payload'), transaction_detail)

        return JsonResponse({"msg": "AuthorizeCaptureAPI post event finished"})


class VoidAPI(AuthorizeNetBaseAPI):

    def post(self, *args, **kwargs):
        logger.info(f"VoidAPI post: Event webhook: {self.request.body}")
        site = get_site_from_request(self.request)
        logger.info(f"VoidAPI post: site: {site}")

        if not self.request.body:
            logger.warning("VoidAPI post: Webhook event has no body")
            return JsonResponse({"msg": "VoidAPI post: Webhook event has no body"})

        if not self.is_valid_post(site):
            logger.error(f"VoidAPI post: Request was denied: {self.request}")
            raise PermissionDenied()
        
        request_data = json.loads(self.request.body)
        logger.info(f"VoidAPI post: request data: {request_data}")

        if request_data.get('eventType') != 'net.authorize.payment.void.created':
            logger.error(f"VoidAPI post: wrong event type: {request_data.get('eventType')}")
            return JsonResponse({"msg": "Event type is incorrect"})
        
        Payment.objects.filter(profile__site=site, transaction=request_data.get('payload').get('id')).update(status=PurchaseStatus.VOID)
        logger.info(f"VoidAPI post: payment with transaction voided: {request_data.get('payload').get('id')}")

        return JsonResponse({"msg": "VoidAPI post: success"})


class SyncSubscriptionsView(View):

    def get(self, *args, **kwargs):
        site = get_site_from_request(self.request)
        sync_subscriptions(site)
        return JsonResponse({'msg': 'Sync Subscriptions Finished'})


class GetSettledTransactionsView(FormMixin, View):
    form_class = DateTimeRangeForm
    success_url = reverse_lazy('vendor:vendor-home')

    def post(self, request, *args, **kwargs):
        form = self.get_form_class()(request.POST)
        site = get_site_from_request(self.request)

        if form.is_valid():
            settle_authorizenet_transactions(site, start_date, end_date)

        return HttpResponseRedirect(self.request.META.get('HTTP_REFERER', self.get_success_url()))