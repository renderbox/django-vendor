"""
Base Payment processor used by all derived processors.
"""
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

    def set_invoice(self, invoice):
        self.invoice = invoice

    def get_payment_model(self, invoice):
        payment = Payment()
        payment.profile = invoice.profile
        payment.amount = invoice.get_amount()
        payment.provider = self.provider
        payment.invoice = invoice

    def amount(self):   # Retrieves the total amount from the invoice
        return 1.00

    def get_checkout_context(self, invoice, **kwargs):
        '''
        The Invoice plus any additional values to include in the payment record.
        '''
        return {'invoice':invoice}

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
        """
        self.pre_authorization()
        self.authorization()
        self.post_authorization()

    def pre_authorization(self):
        """
        Called before the authorization begins.
        """
        vendor_pre_authorization.send(sender=self.__class__, invoice=self.invoice)

    def authorization(self):
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

    def set_amount(self, amount):
        self.status = PurchaseStatus.QUEUED

    def process_payment(self, invoice):
        self.status = PurchaseStatus.ACTIVE
        # Returns a Payment model with a result
