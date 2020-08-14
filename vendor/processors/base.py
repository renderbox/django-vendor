"""
Base Payment processor used by all derived processors.
"""
from vendor.models import Payment

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

    def get_head_javascript(self):
        """
        Scripts that are expected to show in the top of the template.
        """
        pass

    def get_javascript(self):
        """
        Scripts added to the bottom of the page in the normal js location.
        """
        pass

    def get_template(self):
        """
        Unique partial template for the processor
        """
        pass

    def pre_authorization(self):
        """
        Called before the authorization begins.
        """
        pass

    def authorize(self):
        """
        Called to handle the authorization.
        """
        pass

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