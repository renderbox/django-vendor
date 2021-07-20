"""
Base Payment processor used by all derived processors.
"""
import django.dispatch

from django.conf import settings
from django.utils import timezone
from vendor import config
from vendor.models import Payment, Invoice, Receipt
from vendor.models.choice import PurchaseStatus, TermType
from vendor.utils import get_payment_schedule_end_date
##########
# SIGNALS

vendor_pre_authorization = django.dispatch.Signal()
vendor_process_payment = django.dispatch.Signal()
vendor_post_authorization = django.dispatch.Signal()


#############
# BASE CLASS
class PaymentProcessorBase(object):
    """
    Setup the core functionality for all processors.
    """
    API_ENDPOINT = None

    status = None
    invoice = None
    provider = None
    payment = None
    payment_info = {}
    billing_address = {}
    transaction_token = None
    transaction_id = ""
    transaction_submitted = False
    transaction_message = {}
    transaction_response = {}

    def __init__(self, invoice):
        """
        This should not be overriden.  Override one of the methods it calls if you need to.
        """
        self.set_invoice(invoice)
        self.provider = self.__class__.__name__
        self.processor_setup()
        self.set_api_endpoint()

    def set_api_endpoint(self):
        """
        Sets the API endpoint for debugging or production.It is dependent on the VENDOR_STATE
        enviornment variable. Default value is DEBUG for the VENDOR_STATE this function
        should be overwrote upon necesity of each Payment Processor
        """
        if config.VENDOR_STATE == 'DEBUG':
            self.API_ENDPOINT = None
        elif config.VENDOR_STATE == 'PRODUCTION':
            self.API_ENDPOINT = None

    def processor_setup(self):
        """
        This is for setting up any of the settings needed for the payment processing.
        For example, here you would set the
        """
        pass

    def set_payment_info(self, **kwargs):
        self.payment_info = kwargs

    def set_invoice(self, invoice):
        self.invoice = invoice

    def create_payment_model(self):
        """
        Create payment instance with base information to track payment submissions
        """

        self.payment = Payment(profile=self.invoice.profile,
                                                amount=self.invoice.total,
                                                provider=self.provider,
                                                invoice=self.invoice,
                                                created=timezone.now()
                                                )
        self.payment.result['account_number'] = self.payment_info.cleaned_data.get('card_number')[-4:]
        self.payment.result['first'] = True
        self.payment.payee_full_name = self.payment_info.cleaned_data.get('full_name')
        self.payment.payee_company = self.billing_address.cleaned_data.get('company')

        billing_address = self.billing_address.save(commit=False)
        billing_address, created = self.invoice.profile.get_or_create_address(billing_address)
        if created:
            billing_address.profile = self.invoice.profile
            billing_address.save()

        self.payment.billing_address = billing_address
        self.payment.save()

    def save_payment_transaction_result(self, payment_success, transaction_id, result_info):
        """
        Saves the result output of any transaction.
        """
        self.payment.success = payment_success
        self.payment.transaction = transaction_id
        self.payment.result.update(result_info)
        self.payment.save()

    def update_invoice_status(self, new_status):
        """
        Updates the Invoice status if the transaction was submitted.
        Otherwise it returns the invoice to the Cart. The error is saved in
        the payment for the transaction.
        """
        if self.transaction_submitted:
            self.invoice.status = new_status
        else:
            self.invoice.status = Invoice.InvoiceStatus.CART
        self.invoice.save()

    def is_payment_and_invoice_complete(self):
        """
        If payment was successful and invoice status is complete returns True. Otherwise
        false and no receipts should be created.
        """
        if self.payment.success and self.invoice.status == Invoice.InvoiceStatus.COMPLETE:
            return True
        return False

    def create_receipt_by_term_type(self, product, order_item, term_type):
        today = timezone.now()
        receipt = Receipt()
        receipt.profile = self.invoice.profile
        receipt.order_item = order_item
        receipt.transaction = self.payment.transaction
        receipt.meta.update(self.payment.result)
        receipt.meta['payment_amount'] = self.payment.amount
        receipt.status = PurchaseStatus.COMPLETE
        receipt.start_date = today

        if term_type == TermType.PERPETUAL or term_type == TermType.ONE_TIME_USE:
            receipt.auto_renew = False

        if term_type < TermType.PERPETUAL:
            receipt.end_date = get_payment_schedule_end_date(order_item.offer)
            receipt.auto_renew = True

        return receipt

    def create_order_item_receipt(self, order_item):
        """
        Creates a receipt for every product in the order item according to its,
        offering term type.
        """
        for product in order_item.offer.products.all():
            receipt = self.create_receipt_by_term_type(product, order_item, order_item.offer.terms)
            receipt.save()
            receipt.products.add(product)

    def create_receipts(self, order_items):
        """
        It then creates receipt for the order items supplied.
        """
        for order_item in order_items.all():
            self.create_order_item_receipt(order_item)

    def update_subscription_receipt(self, subscription, subscription_id, status):
        """
        subscription: OrderItem
        subscription_id: int
        status: PurchaseStatus
        """
        subscription_receipt = self.invoice.order_items.get(offer=subscription.offer).receipts.get(transaction=self.payment.transaction)
        subscription_receipt.meta['subscription_id'] = subscription_id
        subscription_receipt.status = status
        subscription_receipt.save()

    def amount(self):   # Retrieves the total amount from the invoice
        self.invoice.update_totals()
        return self.invoice.total

    def amount_without_subscriptions(self):
        subscription_total = sum([ oi.total for oi in self.invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION)])

        amount = self.invoice.total - subscription_total
        return amount

    def get_transaction_id(self):
        return "{}-{}-{}-{}".format(self.invoice.profile.pk, settings.SITE_ID, self.invoice.pk, str(self.payment.created)[-12:-6])

    def set_billing_address_form_data(self, form_data, form_class):
        self.billing_address = form_class(form_data)

    def set_payment_info_form_data(self, form_data, form_class):
        self.payment_info = form_class(form_data)

    def is_data_valid(self):
        if not (self.billing_address.is_valid() and self.payment_info.is_valid() and self.invoice and self.invoice.order_items.count()):
            return False
        return True

    # -------------------
    # Data for the View
    def get_checkout_context(self, request=None, context={}):
        '''
        The Invoice plus any additional values to include in the payment record.
        '''
        # context = deepcopy(context)
        context['invoice'] = self.invoice
        return context

    def get_header_javascript(self):
        """
        Scripts that are expected to show in the top of the template.

        This will return a list of relative static URLs to the scripts.
        """
        return []

    def get_javascript(self):
        """
        Scripts added to the bottom of the page in the normal js location.

        This will return a list of relative static URLs to the scripts.
        """
        return []

    def get_template(self):
        """
        Unique partial template for the processor
        """
        pass

    # -------------------
    # Process a Payment
    def authorize_payment(self):
        """
        This runs the chain of events in a transaction.
        This should not be overriden.  Override one of the methods it calls if you need to.
        """
        self.invoice.ordered_date = timezone.now()
        self.invoice.save()
        if not self.invoice.calculate_subtotal():
            self.free_payment()
            return None

        if not self.is_data_valid():
            return None

        self.status = PurchaseStatus.QUEUED     # TODO: Set the status on the invoice.  Processor status should be the invoice's status.
        vendor_pre_authorization.send(sender=self.__class__, invoice=self.invoice)

        self.pre_authorization()

        self.status = PurchaseStatus.ACTIVE     # TODO: Set the status on the invoice.  Processor status should be the invoice's status.
        vendor_process_payment.send(sender=self.__class__, invoice=self.invoice)

        if self.invoice.get_one_time_transaction_order_items():
            self.create_payment_model()
            self.process_payment()
            self.save_payment_transaction_result(self.transaction_submitted, self.transaction_id, self.transaction_response)
            self.update_invoice_status(Invoice.InvoiceStatus.COMPLETE)
            if self.is_payment_and_invoice_complete():
                self.invoice.save_discounts_vendor_notes()
                self.create_receipts(self.invoice.get_one_time_transaction_order_items())

        if self.invoice.get_recurring_order_items():
            self.process_subscriptions()

        vendor_post_authorization.send(sender=self.__class__, invoice=self.invoice)
        self.post_authorization()


        #TODO: Set the status based on the result from the process_payment()

    def pre_authorization(self):
        """
        Called before the authorization begins.
        """
        pass

    def process_payment(self):
        """
        Called to handle the authorization.
        This is where the core of the payment processing happens.
        """
        # Gateway Transaction goes here...

    def free_payment(self):
        """
        Called to handle an invoice with total zero.
        This are the base internal steps to process a free payment.
        """
        self.payment = Payment(profile=self.invoice.profile,
                               amount=self.invoice.total,
                               provider=self.provider,
                               invoice=self.invoice,
                               created=timezone.now()
                               )
        self.payment.save()
        self.transaction_submitted = True
        self.payment.success = True
        self.payment.transaction = f"{self.payment.uuid}-free"
        self.payment.payee_full_name = " ".join([self.invoice.profile.user.first_name, self.invoice.profile.user.last_name])
        self.payment.result = {'first': True}
        self.payment.save()

        self.update_invoice_status(Invoice.InvoiceStatus.COMPLETE)

        self.create_receipts(self.invoice.order_items.all())

    def post_authorization(self):
        """
        Called after the authorization is complete.
        """
        pass

    def capture_payment(self):
        """
        Called to handle the capture.  (some gateways handle this at the same time as authorize_payment() )
        """
        pass

    def void_payment(self):
        """
        Call to handle a payment that has not been settled and wants to be voided
        """
        pass

    # -------------------
    # Process a Subscription
    def process_subscriptions(self):
        """
        Process/subscribies recurring payments throught the payement gateway and creates a payment model for each subscription.
        If a payment is completed it will create a receipt for the subscription
        """
        if not self.is_card_valid():
            return None

        for subscription in self.invoice.get_recurring_order_items():
            self.create_payment_model()
            self.subscription_payment(subscription)
            self.save_payment_transaction_result(self.transaction_submitted, self.transaction_id, self.transaction_response)
            self.update_invoice_status(Invoice.InvoiceStatus.COMPLETE)
            if self.is_payment_and_invoice_complete():
                self.invoice.save_discounts_vendor_notes()
                self.create_order_item_receipt(subscription)

    def subscription_payment(self, subscription):
        """
        Call handels the authrization and creation for a subscription.
        """
        # Gateway Transaction goes here...

    def subscription_info(self):
        pass

    def subscription_update_payment(self):
        pass

    def subscription_cancel(self):
        pass

    def is_card_valid(self):
        """
        Function to validate a credit card by method of makeing a microtransaction and voiding it if authorized.
        """
        pass

    def renew_subscription(self, past_receipt, payment_info):
        """
        Function to renew already paid subscriptions form the payment gateway provider.
        """
        self.payment = Payment(profile=self.invoice.profile,
                               amount=self.invoice.total,
                               invoice=self.invoice,
                               created=timezone.now())
        self.payment.result = payment_info

        self.transaction_submitted = True

        self.payment.success = True
        self.payment.transaction = past_receipt.transaction
        self.payment.payee_full_name = " ".join([self.invoice.profile.user.first_name, self.invoice.profile.user.last_name])

        self.payment.save()

        self.update_invoice_status(Invoice.InvoiceStatus.COMPLETE)

        self.create_receipts(self.invoice.order_items.all())

    # -------------------
    # Refund a Payment

    def refund_payment(self):
        pass
