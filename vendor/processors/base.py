"""
Base Payment processor used by all derived processors.
"""
import django.dispatch

from copy import deepcopy
from datetime import datetime
from django.db.models import Sum
from django.conf import settings
from django.utils import timezone
from vendor.models import Payment, Invoice
from vendor.models.choice import PurchaseStatus
##########
# SIGNALS

vendor_pre_authorization = django.dispatch.Signal()
vendor_post_authorization =  django.dispatch.Signal()

#############
# BASE CLASS

class PaymentProcessorBase(object):
    """
    Setup the core functionality for all processors.
    """
    status = None
    invoice = None
    provider = None
    payment = None
    payment_info = {}
    billing_address = {}
    transaction_token = None
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
        self.payment = Payment(  profile=self.invoice.profile,
                            amount=self.invoice.total,
                            provider=self.provider,
                            invoice=self.invoice,
                            created=timezone.now()
                            )

    def save_payment_transaction(self):
        pass

    def update_invoice_status(self, new_status):
        if self.transaction_submitted:
            self.invoice.status = new_status
        else:
            self.invoice.status = Invoice.InvoiceStatus.FAILED
        self.invoice.save()

    def create_reciepts(self):
        pass

    def amount(self):   # Retrieves the total amount from the invoice
        self.invoice.update_totals()
        return self.invoice.total

    def amount_without_subscriptions(self):
        subscription_total = self.invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION).aggregate(Sum('offer__total'))
        
        subscription_total = sum([ s.total for s in subscriptions ])

        amount = self.invoice.total - subscription_total
        return self.to_valid_decimal(amount)

    def get_transaction_id(self):
        return "{}-{}-{}-{}".format(self.invoice.profile.pk, settings.SITE_ID, self.invoice.pk, str(self.invoice.payments.last().created)[-12:-6])

    def get_billing_address_form_data(self, form_data, form_class, prefix=""):
        self.billing_address = form_class(form_data, prefix=prefix)
    
    def get_payment_info_form_data(self, form_data, form_class, prefix=""):
        self.payment_info = form_class(form_data, prefix=prefix)

    #-------------------
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

    #-------------------
    # Process a Payment

    def authorize_payment(self):
        """
        This runs the chain of events in a transaction.
        
        This should not be overriden.  Override one of the methods it calls if you need to.
        """
        self.status = PurchaseStatus.QUEUED     # TODO: Set the status on the invoice.  Processor status should be the invoice's status.
        vendor_pre_authorization.send(sender=self.__class__, invoice=self.invoice)
        self.pre_authorization()

        self.status = PurchaseStatus.ACTIVE     # TODO: Set the status on the invoice.  Processor status should be the invoice's status.
        self.process_payment()

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
        pass

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

    #-------------------
    # Process a Subscription
    
    def process_subscription(self):
        pass

    def process_update_subscription(self):
        pass

    def process_cancel_subscription(self):
        pass

    #-------------------
    # Refund a Payment

    def refund_payment(self):
        pass

    