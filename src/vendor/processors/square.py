"""
Payment processor for Square https://squareup.com
"""
from .base import PaymentProcessorBase
from vendor.integrations import StripeIntegration

from square import Square
from square.environment import SquareEnvironment

class SquareProcessor(PaymentProcessorBase):
    environment = None
    source = None

    def set_api_endpoint(self):
        """
        Sets the API endpoint for debugging or production.It is dependent on the VENDOR_STATE
        enviornment variable. Default value is DEBUG for the VENDOR_STATE
        """
        print('SET_API_ENDPOINT', VENDOR_STATE)
        if VENDOR_STATE == 'DEBUG':
            self.API_ENDPOINT = "https://connect.squareupsandbox.com"
            self.environment = SquareEnvironment.SANDBOX
        elif VENDOR_STATE == 'PRODUCTION':
            self.API_ENDPOINT = "https://connect.squareup.com"
            self.environment = SquareEnvironment.PRODUCTION

    def processor_setup(self, site, source=None):
        print("PROCESSOR SETUP")
        self.credentials = SquareIntegration(site)
        self.source = source
        self.site = site
        # self.query_builder = StripeQueryBuilder()

        access_token = None
        if self.environment == SquareEnvironment.SANDBOX:
            if settings.SQUARE_SANDBOX_ACCESS_TOKEN:
                access_token = settings.SQUARE_SANDBOX_ACCESS_TOKEN
            else:
                logger.error("SquareProcessor missing key in settings: SQUARE_SANDBOX_ACCESS_TOKEN")
                raise ValueError("SquareProcessor missing key in settings: SQUARE_SANDBOX_ACCESS_TOKEN")
        elif self.environment == SquareEnvironment.PRODUCTION:
            if self.credentials.instance:
                access_token = self.credentials.instance.private_key
            elif settings.SQUARE_ACCESS_TOKEN:
                access_token = settings.SQUARE_ACCESS_TOKEN
            else:
                logger.error("SquareProcessor missing key in settings: SQUARE_ACCESS_TOKEN")
                raise ValueError("SquareProcessor missing key in settings: SQUARE_ACCESS_TOKEN")
        else:
                logger.error("SquareProcessor missing environment setting")
                raise ValueError("SquareProcessor missing environment setting")

        self.square = Square(
            environment=self.environment
            token=access_token
        )
        self.api_version = "2025-04-16"

    def create_square_customer(self, site):
        idempotency_key = uuid()
        self.square.customers.create(
            idempotency_key=idempotency_key,
            address={
                "address_line1": "123 Main St",
                "administrative_district_level1": "AL",
                "country": "US",
                "first_name": "Test",
                "last_name": "User",
                "locality": "Anytown",
                "postal_code": "12345"
            },
            email_address="testuser@x4internet.com"
        )




