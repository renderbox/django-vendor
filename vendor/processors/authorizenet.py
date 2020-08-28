"""
Payment processor for Authorize.net.
"""
from .base import PaymentProcessorBase

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import *
from decimal import *
from django.conf import settings


class AuthorizeNetProcessor(PaymentProcessorBase):
    AUTHORIZE_CAPUTRE_TRANSACTION = "authCaptureTransaction"

    API_ENDPOINTS = [
        AUTHORIZE_CAPUTRE_TRANSACTION
    ]

    def __init__(self):
        self.merchantAuth = apicontractsv1.merchantAuthenticationType()

    def __str__(self):
        return 'Authorize.Net'

    def get_checkout_context(self, invoice, **kwargs):
        '''
        The Invoice plus any additional values to include in the payment record.
        '''
        self.merchantAuth.transactionKey = settings.AUTHORIZE_NET_TRANSACTION_KEY
        self.merchantAuth.name = settings.AUTHORIZE_NET_API_ID

    def init_transaction(self, reference_id):
        self.transaction = apicontractsv1.createTransactionRequest()
        self.transaction.merchantAuthentication = self.merchantAuth
        # str("-".join([str(invoice.profile.pk), str(settings.SITE_ID), str(invoice.pk)]))
        self.transaction.refId = reference_id

    def init_transaction_request(self, transaction_type, amount):
        self.transaction_request = apicontractsv1.transactionRequestType()
        self.transaction_request.transactionType = transaction_type
        self.transaction_request.amount = Decimal(
            amount).quantize(Decimal('.00'), rounding=ROUND_DOWN)

    def set_payment_type_credit_card(self, card):
        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = str(card.data['card_number'])
        creditCard.expirationDate = str(
            "-".join([card.data['expire_year'], card.data['expire_month']]))
        creditCard.cardCode = str(card.data['cvv_number'])
        return creditCard

    def set_transaction_request_payment(self, payment_data):
        payment = apicontractsv1.paymentType()
        payment.creditCard = self.set_payment_type_credit_card(payment_data)
        self.transaction_request.payment = payment

    def set_transaction_request(self):
        self.transaction.transactionRequest = self.transaction_request

    def init_transaction_controller(self):
        self.transaction_controller = createTransactionController(
            self.transaction)

    def execute_transaction(self):
        self.transaction_controller.execute()
        return self.transaction_controller.getresponse()

    def set_transaction_request_settings(self, settings):
        pass

    def set_transaction_request_client_ip(self, client_ip):
        pass

    def init_line_item(self, item):
        line_item = apicontractsv1.lineItemType()
        line_item.itemId = str(item.pk)
        line_item.name = item.name
        line_item.description = item.offer.product.description
        line_item.quantity = str(item.quantity)
        line_item.unitPrice = str(item.price)
        return line_item

    def set_transaction_request_line_items(self, items):
        line_items = apicontractsv1.ArrayOfLineItem()
        for item in items:
            line_items.append(self.init_line_item(item))
        self.transaction_request.lineItems = line_items

    def set_transaction_request_tax(self, tax):
        pass

    def set_transaction_request_duty(self):
        pass

    def set_transaction_request_shipping(self, shipping):
        pass

    def set_transaction_request_ship_to(self, shipping):
        ship_to = apicontractsv1.customerAddressType()
        ship_to.firstName = "Ellen"
        ship_to.lastName = "Johnson"
        ship_to.company = ""
        ship_to.address = str(",".join([shipping.data.get('address_line_1', ""), shipping.data.get('address_line_2', "")]))
        ship_to.city = str(shipping.data.get("city", ""))
        ship_to.state = str(shipping.data.get("state", ""))
        ship_to.zip = str(shipping.data.get("postal_code"))
        ship_to.country = str(shipping.data.get("country"))
        self.transaction_request.shipTo = ship_to

    def set_transaction_request_billing(self, billing_info):
        billing_address = apicontractsv1.customerAddressType()
        billing_address.firstName = "Ellen"
        billing_address.lastName = "Johnson"
        billing_address.company = ""
        billing_address.address = str(",".join([billing_info.data.get('address_line_1', ""), billing_info.data.get('address_line_2', "")]))
        billing_address.city = str(billing_info.data.get("city", ""))
        billing_address.state = str(billing_info.data.get("state", ""))
        billing_address.zip = str(billing_info.data.get("postal_code"))
        billing_address.country = str(billing_info.data.get("country"))
        self.transaction_request.billTo = billing_address

    def set_transaction_request_customer(self):
        pass

    def check_response(self, response):
        transaction_response = {}
        transaction_response['success'] = False
        transaction_response['msg'] = ""
        if response is not None:
            # Check to see if the API request was successfully received and acted upon
            if response.messages.resultCode == "Ok":
                # Since the API request was successful, look for a transaction response
                # and parse it to display the results of authorizing the card
                if hasattr(response.transactionResponse, 'messages') is True:
                    transaction_response['success'] = True
                    transaction_response['msg'] = "Payment Complete"
                    transaction_response['trans_id'] = response.transactionResponse.transId
                    transaction_response['response_code'] = response.transactionResponse.responseCode
                    transaction_response['code'] = response.transactionResponse.messages.message[0].code
                    transaction_response['message'] = response.transactionResponse.messages.message[0].description
                else:
                    transaction_response['msg'] = 'Failed Transaction.'
                    if hasattr(response.transactionResponse, 'errors') is True:
                        transaction_response['error_code'] = response.transactionResponse.errors.error[0].errorCode
                        transaction_response['error_text'] = response.transactionResponse.errors.error[0].errorText
            # Or, print errors if the API request wasn't successful
            else:
                transaction_response['msg'] = 'Failed Transaction.'
                if hasattr(response, 'transactionResponse') is True and hasattr(response.transactionResponse, 'errors') is True:
                    transaction_response['error_code'] = response.transactionResponse.errors.error[0].errorCode
                    transaction_response['error_text'] = response.transactionResponse.errors.error[0].errorText
                else:
                    transaction_response['error_code'] = response.messages.message[0]['code'].text
                    transaction_response['error_text'] = response.messages.message[0]['text'].text
        else:
            transaction_response['msg'] = 'Null Response.' 

        return transaction_response

    def auth_capture(self, invoice, billing_info, kwargs):
        if not self.merchantAuth.name or not self.merchantAuth.transactionKey:
            return "error", False

        # Init transaction
        self.init_transaction(
            str("-".join([str(invoice.profile.pk), str(settings.SITE_ID), str(invoice.pk)])))

        # Init the transaction request and payment
        self.init_transaction_request(
            AuthorizeNetProcessor.AUTHORIZE_CAPUTRE_TRANSACTION, invoice.total)
        self.set_transaction_request_payment(billing_info)
        self.set_transaction_request_billing(billing_info)

        if invoice.order_items:
            self.set_transaction_request_line_items(invoice.order_items.all())
        if invoice.tax:
            self.set_transaction_request_tax(invoice.tax)
        if invoice.shipping:
            self.set_transaction_request_shipping(invoice.shipping)
        if invoice.shipping_address:
            self.set_transaction_request_ship_to(invoice.shipping_address)

        # You set the request to the transaction
        self.set_transaction_request()

        # Init the Controller with the transaction
        self.init_transaction_controller()

        # You execute and get the response
        response = self.execute_transaction()

        transaction_response = self.check_response(response)
        return transaction_response
