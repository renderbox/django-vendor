"""
Payment processor for Authorize.net.
"""
from .base import PaymentProcessorBase

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import *
from decimal import *
from django.conf import settings

class AuthorizeNetProcessor(PaymentProcessorBase):

    def __init__(self):
        self.merchantAuth = apicontractsv1.merchantAuthenticationType()
        self.merchantAuth.name = settings.AUTHORIZE_NET_API_ID
        self.merchantAuth.transactionKey = settings.AUTHORIZE_NET_TRANSACTION_KEY

    def get_checkout_context(self, invoice, **kwargs):
        '''
        The Invoice plus any additional values to include in the payment record.
        '''
        pass

    def auth_capture(self, invoice, kwargs):

        creditCard = apicontractsv1.creditCardType()

        creditCard.cardNumber = "4111111111111111"
        creditCard.expirationDate = "2020-12"
        creditCard.cardCode = "999"

        payment = apicontractsv1.paymentType()
        payment.creditCard = creditCard

        transactionrequest = apicontractsv1.transactionRequestType()
        transactionrequest.transactionType = "authCaptureTransaction"
        transactionrequest.amount = Decimal('1.55')
        transactionrequest.payment = payment


        createtransactionrequest = apicontractsv1.createTransactionRequest()
        createtransactionrequest.merchantAuthentication = self.merchantAuth
        createtransactionrequest.refId = "123456"

        createtransactionrequest.transactionRequest = transactionrequest
        createtransactioncontroller = createTransactionController(createtransactionrequest)
        createtransactioncontroller.execute()

        response = createtransactioncontroller.getresponse()

        if (response.messages.resultCode == "Ok"):
            print(f"Transaction ID : {response.transactionResponse.transId}")
        else:
            print(f"response code: {response.messages.resultCode}")
