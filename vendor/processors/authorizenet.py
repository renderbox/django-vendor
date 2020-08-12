"""
Payment processor for Authorize.net.
"""
from .base import PaymentProcessorBase

class AuthorizeNetProcessor(PaymentProcessorBase):

    def get_checkout_context(self, invoice, **kwargs):
        '''
        The Invoice plus any additional values to include in the payment record.
        '''
        return {'invoice':invoice}
