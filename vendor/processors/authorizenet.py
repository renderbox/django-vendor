"""
Payment processor for Authorize.net.
"""
import ast

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import *
from django.conf import settings
from decimal import Decimal, ROUND_DOWN
from vendor.choices import PaymentTypes
from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.models.invoice import Invoice

from .base import PaymentProcessorBase, TransactionTypes

class AuthorizeNetProcessor(PaymentProcessorBase):
    """
    Implementation of Authoirze.Net SDK
    https://apitest.authorize.net/xml/v1/schema/AnetApiSchema.xsd
    """
    
    AUTHORIZE = "authOnlyTransaction"
    AUTHORIZE_CAPTURE = "authCaptureTransaction"
    CAPTURE = "captureOnlyTransaction"
    REFUND = "refundTransaction"
    PRIOR_AUTHORIZE_CAPTURE = "priorAuthCaptureTransaction"
    VOID = "voidTransaction"
    GET_DETAILS = "getDetailsTransaction"
    AUTHORIZE_CONTINUE = "authOnlyContinueTransaction"
    AUTHORIZE_CAPTURE_CONTINUE = "authCaptureContinueTransaction"

    GET_SETTLED_BATCH_LIST = "getSettledBatchListRequest"

    """
    Controller executes the transaction, that process a transaction type
    """
    controller = None
    transaction = None
    merchant_auth = None
    transaction_type = None
    
    def __str__(self):
        return 'Authorize.Net'

    def get_checkout_context(self, request=None, context={}):
        context = super().get_checkout_context(context=context)
        # TODO: prefix should be defined somewhere
        context['credit_card_form'] = CreditCardForm(prefix='credit-card', initial={'payment_type': PaymentTypes.CREDIT_CARD})
        context['billing_address_form'] = BillingAddressForm(prefix='billing-address')
        return context
    
    def processor_setup(self):
        """
        Merchant Information needed to aprove the transaction. 
        """
        if not (settings.AUTHORIZE_NET_TRANSACTION_KEY and settings.AUTHORIZE_NET_API_ID):
            raise ValueError("Missing Authorize.net keys in settings: AUTHORIZE_NET_TRANSACTION_KEY and/or AUTHORIZE_NET_API_ID")
        self.merchant_auth = apicontractsv1.merchantAuthenticationType()
        self.merchant_auth.transactionKey = settings.AUTHORIZE_NET_TRANSACTION_KEY
        self.merchant_auth.name = settings.AUTHORIZE_NET_API_ID
        self.init_payment_type_switch()
        self.init_transaction_types()

    def init_transaction_types(self):
        self.transaction_types = {
            TransactionTypes.AUTHORIZE: self.AUTHORIZE,
            TransactionTypes.CAPTURE: self.CAPTURE,
            TransactionTypes.REFUND: self.REFUND,
        }
    
    def init_payment_type_switch(self):
        """
        Initializes the Payment Types create functions
        """
        self.payment_type_switch = {
            PaymentTypes.CREDIT_CARD: self.create_credit_card_payment,
            PaymentTypes.BANK_ACCOUNT: self.create_bank_account_payment,
            PaymentTypes.PAY_PAL: self.create_pay_pay_payment,
            PaymentTypes.MOBILE: self.create_mobile_payment,
        }

    def create_transaction(self):
        """
        This creates the main transaction to be processed.
        """
        transaction = apicontractsv1.createTransactionRequest()
        transaction.merchantAuthentication = self.merchant_auth
        transaction.refId = self.get_transaction_id()
        return transaction

    def create_transaction_type(self, trans_type):
        """
        Creates the transaction type instance with the amount
        """
        transaction_type = apicontractsv1.transactionRequestType()
        transaction_type.transactionType = trans_type
        return transaction_type

    def create_credit_card_payment(self):
        """
        Creates and credit card payment type instance form the payment information set. 
        """
        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = self.payment_info.data.get('credit-card-card_number')
        creditCard.expirationDate = "-".join([self.payment_info.data.get('credit-card-expire_year'), self.payment_info.data.get('credit-card-expire_month')])
        creditCard.cardCode = self.payment_info.data.get('credit-card-cvv_number')
        return creditCard

    def create_bank_account_payment(self):
        raise NotImplementedError

    def create_pay_pay_payment(self):
        raise NotImplementedError

    def create_mobile_payment(self):
        raise NotImplementedError

    def create_payment(self):
        """
        Creates a payment instance acording to the billing information captured
        """
        payment = apicontractsv1.paymentType()
        payment.creditCard = self.payment_type_switch[int(self.payment_info.data.get('credit-card-payment_type'))]()
        return payment

    def set_transaction_request_settings(self, settings):
        raise NotImplementedError

    def set_transaction_request_client_ip(self, client_ip):
        raise NotImplementedError

    def create_line_item(self, item):
        """
        Create a single line item (products) that is attached to a line item array
        """
        line_item = apicontractsv1.lineItemType()
        line_item.itemId = str(item.pk)
        line_item.name = item.name
        line_item.description = item.offer.product.description
        line_item.quantity = str(item.quantity)
        line_item.unitPrice = str(item.price)
        return line_item

    def create_line_item_array(self, items):
        """
        Creates a list o line items(products) that are attached to the transaction type
        """
        line_items = apicontractsv1.ArrayOfLineItem()
        for item in items:
            line_items.append(self.create_line_item(item))
        return line_items

    def create_tax(self, tax):
        raise NotImplementedError

    def create_shipping(self, shipping):
        raise NotImplementedError

    def create_billing_address(self):
        """
        Creates Billing address to improve security in transaction
        """
        billing_address = apicontractsv1.customerAddressType()
        billing_address.firstName = " ".join(self.payment_info.data.get('credit-card-full_name', "").split(" ")[:-1])
        billing_address.lastName = self.payment_info.data.get('credit-card-full_name', "").split(" ")[-1]
        billing_address.company = self.billing_address.data.get('billing-address-company')
        billing_address.address = str(", ".join([self.billing_address.data.get('billing-address-address_1'), self.billing_address.data.get('billing-address-address_2')]))
        billing_address.city = str(self.billing_address.data.get("billing-address-city", ""))
        billing_address.state = str(self.billing_address.data.get("billing-address-state", ""))
        billing_address.zip = str(self.billing_address.data.get("billing-address-postal_code"))
        billing_address.country = str(self.billing_address.data.get("billing-address-country"))
        return billing_address

    def create_customer(self):
        raise NotImplementedError

    def check_response(self, response):
        """
        Checks the transaction response and set the transaction_result and transaction_response variables
        """
        self.transaction_response = response.transactionResponse
        self.transaction_message = {}
        self.transaction_result = False
        self.transaction_message['msg'] = ""
        if response is not None:
            # Check to see if the API request was successfully received and acted upon
            if response.messages.resultCode == "Ok":
                # Since the API request was successful, look for a transaction response
                # and parse it to display the results of authorizing the card
                if hasattr(response.transactionResponse, 'messages') is True:
                    self.transaction_result = True
                    self.transaction_message['msg'] = "Payment Complete"
                    self.transaction_message['trans_id'] = response.transactionResponse.transId
                    self.transaction_message['response_code'] = response.transactionResponse.responseCode
                    self.transaction_message['code'] = response.transactionResponse.messages.message[0].code
                    self.transaction_message['message'] = response.transactionResponse.messages.message[0].description
                else:
                    self.transaction_message['msg'] = 'Failed Transaction.'
                    if hasattr(response.transactionResponse, 'errors') is True:
                        self.transaction_message['error_code'] = response.transactionResponse.errors.error[0].errorCode
                        self.transaction_message['error_text'] = response.transactionResponse.errors.error[0].errorText
            # Or, print errors if the API request wasn't successful
            else:
                self.transaction_message['msg'] = 'Failed Transaction.'
                if hasattr(response, 'transactionResponse') is True and hasattr(response.transactionResponse, 'errors') is True:
                    self.transaction_message['error_code'] = response.transactionResponse.errors.error[0].errorCode
                    self.transaction_message['error_text'] = response.transactionResponse.errors.error[0].errorText
                else:
                    self.transaction_message['error_code'] = response.messages.message[0]['code'].text
                    self.transaction_message['error_text'] = response.messages.message[0]['text'].text
        else:
            self.transaction_message['msg'] = 'Null Response.'

    def get_form_data(self, form_data):
        self.payment_info = CreditCardForm(dict([d for d in form_data.items() if 'credit-card' in d[0]]), prefix='credit-card')
        self.billing_address = BillingAddressForm(dict([d for d in form_data.items() if 'billing-address' in d[0]]), prefix='billing-address')
        
    def save_payment_transaction(self):
        self.payment = self.get_payment_model()        
        self.payment.success = self.transaction_result
        self.payment.transaction = self.transaction_response.get('transId', "Transaction Faild")
        response = self.transaction_response.__dict__
        if 'errors' in response:
            response.pop('errors')
        if 'messages' in response:
            response.pop('messages')
        self.payment.result = str({**self.transaction_message, **response})
        self.payment.payee_full_name = self.payment_info.data.get('credit-card-full_name')
        self.payment.payee_company = self.billing_address.data.get('billing-address-company')
        billing_address = self.billing_address.save(commit=False)
        billing_address.profile = self.invoice.profile
        billing_address.save()
        self.payment.billing_address = billing_address
        self.payment.save()

    def check_transaction_keys(self):
        """
        Checks if the transaction keys have been set otherwise the transaction should not continue
        """
        if not self.merchant_auth.name or not self.merchant_auth.transactionKey:
            self.transaction_result = False
            self.transaction_response = {'msg': "Make sure you run processor_setup before process_payment and that envarionment keys are set"}
            return True
        else:
            return False

    def update_invoice_status(self, new_status):
        if self.transaction_result:
            self.invoice.status = new_status
        else:
            self.invoice.status = Invoice.InvoiceStatus.FAILED
        self.invoice.save()

    def process_payment(self, request):
        if self.check_transaction_keys():
            return

        # Process form data to set up transaction
        self.get_form_data(request.POST)

        # Init transaction
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(settings.AUTHOIRZE_NET_TRANSACTION_TYPE_DEFAULT)
        self.transaction_type.amount = Decimal(self.invoice.total).quantize(Decimal('.00'), rounding=ROUND_DOWN)
        self.transaction_type.payment = self.create_payment()
        self.transaction_type.billTo = self.create_billing_address()

        # Optional items for make it easier to read and use on the Authorize.net portal.
        if self.invoice.order_items:
            self.transaction_type.lineItems = self.create_line_item_array(self.invoice.order_items.all())

        # You set the request to the transaction
        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.controller.execute()

        # You execute and get the response
        response = self.controller.getresponse()
        self.check_response(response)

        self.save_payment_transaction()

        self.update_invoice_status(Invoice.InvoiceStatus.COMPLETE)

    def refund_payment(self, payment):
        if self.check_transaction_keys():
            return

        # Init transaction
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(self.transaction_types[TransactionTypes.REFUND])
        self.transaction_type.amount = Decimal(self.invoice.total).quantize(Decimal('.00'), rounding=ROUND_DOWN)
        self.transaction_type.refTransId = ast.literal_eval(payment.result).get('refTransID')

        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = ast.literal_eval(payment.result).get('accountNumber')[-4:]
        creditCard.expirationDate = "XXXX"

        payment = apicontractsv1.paymentType()
        payment.creditCard =  creditCard
        self.transaction_type.payment = payment        

        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.controller.execute()

        response = self.controller.getresponse()
        self.check_response(response)

        self.update_invoice_status(Invoice.InvoiceStatus.REFUNDED)

    def get_settled_batch_list(self):
        if self.check_transaction_keys():
            return 

        settledBatchListRequest = apicontractsv1.getSettledBatchListRequest()
        settledBatchListRequest.merchantAuthentication = self.merchant_auth

        settledBatchListController = getSettledBatchListController(settledBatchListRequest)
        settledBatchListController.execute()

        response = settledBatchListController.getresponse()

    def get_transaction_batch_list(self, batch_id):

        # set sorting parameters
        sorting = apicontractsv1.TransactionListSorting()
        sorting.orderBy = apicontractsv1.TransactionListOrderFieldEnum.id
        sorting.orderDescending = True

        # set paging and offset parameters
        paging = apicontractsv1.Paging()
        # Paging limit can be up to 1000 for this request
        paging.limit = 20
        paging.offset = 1

        transactionListRequest = apicontractsv1.getTransactionListRequest()
        transactionListRequest.merchantAuthentication = self.merchant_auth
        transactionListRequest.refId = 
        transactionListRequest.batchId = batch_id
        transactionListRequest.sorting = sorting
        transactionListRequest.paging = paging

        self.controller = getTransactionListController(transactionListRequest)
        self.controller.execute()

    