"""
Payment processor for Square https://squareup.com
"""
from .base import PaymentProcessorBase


class SquareProcessor(PaymentProcessorBase):

    def set_api_endpoint(self):
        """
        Sets the API endpoint for debugging or production.It is dependent on the VENDOR_STATE
        enviornment variable. Default value is DEBUG for the VENDOR_STATE
        """
        print('SET_API_ENDPOINT')
        if VENDOR_STATE == 'DEBUG':
            self.API_ENDPOINT = "https://connect.squareupsandbox.com"
        elif VENDOR_STATE == 'PRODUCTION':
            self.API_ENDPOINT = "https://connect.squareup.com"