"""
Base Payment processor used by all derived processors.
"""
import django.dispatch

from copy import deepcopy
from django.conf import settings
from enum import Enum, auto
from vendor.models import Payment
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
    transaction_result = None
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

    def get_payment_model(self):
        payment = Payment(  profile=self.invoice.profile,
                            amount=self.invoice.total,
                            provider=self.provider,
                            invoice=self.invoice
                            )
        return payment

    def save_payment_transaction(self):
        pass

    def amount(self):   # Retrieves the total amount from the invoice
        self.invoice.update_totals()
        return self.invoice.total

    def get_transaction_id(self):
        return "{}-{}-{}".format(self.invoice.profile.pk, settings.SITE_ID, self.invoice.pk)

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
    # Refund a Payment

    def refund_payment(self):
        pass
