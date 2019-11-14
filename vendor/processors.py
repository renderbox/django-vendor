# Payment Processors

from vendor.models import PurchaseStatus

class PaymentProcessorBase():
    '''
    Setup the core functionality for all processors.

    '''
    status = None

    def set_amount(self, amount):
        self.status = PurchaseStatus.QUEUED

    def process_payment(self):
        self.status = PurchaseStatus.ACTIVE


class StripeProcessor(PaymentProcessorBase):
    pass
