"""
Base Payment processor used by all derived processors.
"""
from copy import deepcopy

import django.dispatch

from vendor.models import Payment
from vendor.models.choice import PurchaseStatus

##########
# SIGNALS

vendor_pre_authorization = django.dispatch.Signal()
vendor_post_authorization =  django.dispatch.Signal()


#############
# BASE CLASS

class PaymentProcessorBase():
    """
    Setup the core functionality for all processors.
    """
    status = None
    invoice = None
    provider = None
    payment_info = None
    billing_address = None
    transaction_token = None

    def __init__(self, invoice):
        """
        This should not be overriden.  Override one of the methods it calls if you need to.
        """
        self.set_invoice(invoice)
        self.processor_setup()

    def processor_setup(self):
        pass

    def set_invoice(self, invoice):
        self.invoice = invoice

    def get_payment_model(self):
        payment = Payment(  profile=self.invoice.profile,
                            amount=invoice.get_amount(),
                            provider=self.provider,
                            invoice=self.invoice
                            )
        return payment

    def amount(self):   # Retrieves the total amount from the invoice
        self.invoice.update_totals()
        return self.invoice.total

    def get_checkout_context(self, request=None, context={}):
        '''
        The Invoice plus any additional values to include in the payment record.
        '''
        context = deepcopy(context)
        context['invoice'] = self.invoice
        return context

    def get_header_javascript(self):
        """
        Scripts that are expected to show in the top of the template.

        This will return a list of relative static URLs to the scripts.
        """
        return []

    def get_footer_javascript(self):
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

    def authorize(self):
        """
        This runs the chain of events in a transaction.
        
        This should not be overriden.  Override one of the methods it calls if you need to.
        """
        self.status = PurchaseStatus.QUEUED     # TODO: Set the status on the invoice.  Processor status should be the invoice's status.
        self.pre_authorization()

        self.status = PurchaseStatus.ACTIVE     # TODO: Set the status on the invoice.  Processor status should be the invoice's status.
        self.process_payment()

        self.post_authorization()

    def pre_authorization(self):
        """
        Called before the authorization begins.
        """
        vendor_pre_authorization.send(sender=self.__class__, invoice=self.invoice)

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
        vendor_post_authorization.send(sender=self.__class__, invoice=self.invoice)

    def capture(self):
        """
        Called to handle the capture.  (some gateways handle this at the same time as authorize() )
        """
        pass

    def settlement(self):
        pass
