"""
Payment processor for Authorize.net.
"""
import ast

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import *
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from django.conf import settings
from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.models.choice import TransactionTypes, PaymentTypes, TermType
from vendor.models.invoice import Invoice
from vendor.models.address import Country
from .base import PaymentProcessorBase


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
        context['credit_card_form'] = CreditCardForm(
            prefix='credit-card', initial={'payment_type': PaymentTypes.CREDIT_CARD})
        context['billing_address_form'] = BillingAddressForm(
            prefix='billing-address')
        return context

    def processor_setup(self):
        """
        Merchant Information needed to aprove the transaction. 
        """
        if not (settings.AUTHORIZE_NET_TRANSACTION_KEY and settings.AUTHORIZE_NET_API_ID):
            raise ValueError(
                "Missing Authorize.net keys in settings: AUTHORIZE_NET_TRANSACTION_KEY and/or AUTHORIZE_NET_API_ID")
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

    def check_transaction_keys(self):
        """
        Checks if the transaction keys have been set otherwise the transaction should not continue
        """
        if not self.merchant_auth.name or not self.merchant_auth.transactionKey:
            self.transaction_result = False
            self.transaction_response = {
                'msg': "Make sure you run processor_setup before process_payment and that envarionment keys are set"}
            return True
        else:
            return False
    ##########
    # Authorize.net Object creations
    ##########

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
        transaction_type.currencyCode = 'USD'
        return transaction_type

    def create_credit_card_payment(self):
        """
        Creates and credit card payment type instance form the payment information set. 
        """
        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = self.payment_info.data.get(
            'credit-card-card_number')
        creditCard.expirationDate = "-".join([self.payment_info.data.get(
            'credit-card-expire_year'), self.payment_info.data.get('credit-card-expire_month')])
        creditCard.cardCode = self.payment_info.data.get(
            'credit-card-cvv_number')
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
        payment.creditCard = self.payment_type_switch[int(
            self.payment_info.data.get('credit-card-payment_type'))]()
        return payment

    def create_customer_data(self):
        customerData = apicontractsv1.customerDataType()
        customerData.type = "individual"
        customerData.id = str(self.invoice.profile.user.pk)
        customerData.email = self.invoice.profile.user.email
        return customerData

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
            line_items.lineItem.append(self.create_line_item(item))
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
        billing_address.firstName = " ".join(self.payment_info.data.get(
            'credit-card-full_name', "").split(" ")[:-1])
        billing_address.lastName = self.payment_info.data.get(
            'credit-card-full_name', "").split(" ")[-1]
        billing_address.company = self.billing_address.data.get(
            'billing-address-company')
        billing_address.address = str(", ".join([self.billing_address.data.get(
            'billing-address-address_1'), self.billing_address.data.get('billing-address-address_2')]))
        billing_address.city = str(
            self.billing_address.data.get("billing-address-city", ""))
        billing_address.state = str(
            self.billing_address.data.get("billing-address-state", ""))
        billing_address.zip = str(
            self.billing_address.data.get("billing-address-postal_code"))
        country = Country(
            int(self.billing_address.data.get("billing-address-country")))
        billing_address.country = str(country.name)
        return billing_address

    def create_customer(self):
        raise NotImplementedError

    def create_payment_scheduale_interval_type(self, period_length, payment_occurrences, trial_occurrences=0):
        """
        Create an interval schedule with fixed months.
        period_length: The period length the service payed mor last 
            eg: period_length = 2. the user will be billed every 2 months.
        payment_occurrences: The number of occurrences the payment should be made.
            eg: payment_occurrences = 6. There will be six payments made at each period_length.
        trial_occurrences: The number of ignored payments out of the payment_occurrences
        """
        payment_schedule = apicontractsv1.paymentScheduleType()
        payment_schedule.interval = apicontractsv1.paymentScheduleTypeInterval()
        payment_schedule.interval.length = period_length
        payment_schedule.interval.unit = apicontractsv1.ARBSubscriptionUnitEnum.months
        payment_schedule.startDate = datetime.now()
        payment_schedule.totalOccurrences = payment_occurrences
        payment_schedule.trialOccurrences = trial_occurrences
    ##########
    # Django-Vendor to Authoriaze.net data exchange functions
    ##########
    def get_form_data(self, form_data):
        self.payment_info = CreditCardForm(dict(
            [d for d in form_data.items() if 'credit-card' in d[0]]), prefix='credit-card')
        self.billing_address = BillingAddressForm(dict(
            [d for d in form_data.items() if 'billing-address' in d[0]]), prefix='billing-address')

    def save_payment_transaction(self):
        self.payment = self.get_payment_model()
        self.payment.success = self.transaction_result
        self.payment.transaction = self.transaction_response.get(
            'transId', "Transaction Faild")
        response = self.transaction_response.__dict__
        if 'errors' in response:
            response.pop('errors')
        if 'messages' in response:
            response.pop('messages')
        self.payment.result = str({**self.transaction_message, **response})
        self.payment.payee_full_name = self.payment_info.data.get(
            'credit-card-full_name')
        self.payment.payee_company = self.billing_address.data.get(
            'billing-address-company')
        billing_address = self.billing_address.save(commit=False)
        billing_address.profile = self.invoice.profile
        billing_address.save()
        self.payment.billing_address = billing_address
        self.payment.save()

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

    def update_invoice_status(self, new_status):
        if self.transaction_result:
            self.invoice.status = new_status
        else:
            self.invoice.status = Invoice.InvoiceStatus.FAILED
        self.invoice.save()

    def get_amount_without_subscriptions(self):
        subscriptions = self.invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION)
        
        subscription_total = sum([ s.total for s in subscriptions ])

        amount = self.invoice.total - subscription_total
        return Decimal(amount).quantize(Decimal('.00'), rounding=ROUND_DOWN)
    ##########
    # Processor Transactions
    ##########
    def process_payment(self, request):
        if self.check_transaction_keys():
            return

        # Process form data to set up transaction
        self.get_form_data(request.POST)

        # Init transaction
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(
            settings.AUTHOIRZE_NET_TRANSACTION_TYPE_DEFAULT)
        self.transaction_type.amount = self.get_amount_without_subscriptions()
        self.transaction_type.payment = self.create_payment()
        self.transaction_type.billTo = self.create_billing_address()

        # Optional items for make it easier to read and use on the Authorize.net portal.
        if self.invoice.order_items:
            self.transaction_type.lineItems = self.create_line_item_array(
                self.invoice.order_items.all())

        # You set the request to the transaction
        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.controller.execute()

        # You execute and get the response
        response = self.controller.getresponse()
        self.check_response(response)

        self.save_payment_transaction()

        self.update_invoice_status(Invoice.InvoiceStatus.COMPLETE)


    def create_subscriptions(self, request):
        if self.check_transaction_keys():
            return
        subscription_list = self.invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION)
        if not subscription_list:
            return
        self.get_form_data(request.POST)

        for subscription in subscription_list:
            self.create_subscription(subscription)

    
    
    def create_subscription(self, subscription):
        """
        Creates a subscription for a user. Subscriptions can be monthy or yearly.objects.all()
        """
        period_length = str(ast.literal_eval(subscription.offer.term_details).get('period_length'))
        payment_occurrences = ast.literal_eval(subscription.offer.term_details).get('payment_occurrences')
        trail_occurrences = ast.literal_eval(subscription.offer.term_details).get('trial_occurrences', 0)
        
        # Setting billing information
        billto = apicontractsv1.nameAndAddressType()
        billto.firstName = " ".join(self.payment_info.data.get('credit-card-full_name', "").split(" ")[:-1])
        billto.lastName = self.payment_info.data.get('credit-card-full_name', "").split(" ")[-1]

        # Setting subscription details
        self.transaction_type = apicontractsv1.ARBSubscriptionType()
        self.transaction_type.name = subscription.offer.name
        self.transaction_type.paymentSchedule = self.create_payment_scheduale_interval_type(period_length, payment_occurrences)
        self.transaction_type.amount = Decimal(subscription.total).quantize(Decimal('.00'), rounding=ROUND_DOWN)
        self.transaction_type.trialAmount = Decimal('0.00')
        self.transaction_type.billTo = billto
        self.transaction_type.payment = self.create_payment()

        # Creating the request
        self.transaction = apicontractsv1.ARBCreateSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscription = self.transaction_type
        
        # Creating and executing the controller
        self.controller = ARBCreateSubscriptionController(self.transaction)
        self.controller.execute()
        # Getting the response
        response = self.controller.getresponse()
     
        # Save Payment
        


    def refund_payment(self, payment):
        if self.check_transaction_keys():
            return

        # Init transaction
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(
            self.transaction_types[TransactionTypes.REFUND])
        self.transaction_type.amount = Decimal(payment.amount).quantize(
            Decimal('.00'), rounding=ROUND_DOWN)
        self.transaction_type.refTransId = payment.transaction

        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = ast.literal_eval(
            payment.result).get('accountNumber')[-4:]
        creditCard.expirationDate = "XXXX"

        payment_type = apicontractsv1.paymentType()
        payment_type.creditCard = creditCard
        self.transaction_type.payment = payment_type

        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.controller.execute()

        response = self.controller.getresponse()
        self.check_response(response)

        if self.transaction_result:
            self.update_invoice_status(Invoice.InvoiceStatus.REFUNDED)

    ##########
    # Reporting API, for transaction retrieval information
    ##########
    def get_settled_batch_list(self, start_date, end_date):
        """
        Gets a list of batches for settled transaction between the start and end date.
        """
        self.transaction = apicontractsv1.getSettledBatchListRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.firstSettlementDate = start_date
        self.transaction.lastSettlementDate = end_date

        self.controller = getSettledBatchListController(self.transaction)
        self.controller.execute()

        response = self.controller.getresponse()

        if response.messages.resultCode == apicontractsv1.messageTypeEnum.Ok and hasattr(response, 'batchList'):
            return [batch for batch in response.batchList.batch]

    def get_transaction_batch_list(self, batch_id):
        """
        Gets the list of settled transaction in a batch. There are sorting and paging option
        that are not currently implemented. It will get the last 1k transactions.
        """
        self.transaction = apicontractsv1.getTransactionListRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.batchId = batch_id

        self.controller = getTransactionListController(self.transaction)
        self.controller.execute()

        response = self.controller.getresponse()

        if response.messages.resultCode == apicontractsv1.messageTypeEnum.Ok and hasattr(response, 'transactions'):
            return [transaction for transaction in response.transactions.transaction]

    def get_transaction_detail(self, transaction_id):
        self.transaction = apicontractsv1.getTransactionDetailsRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.transId = transaction_id

        self.controller = getTransactionDetailsController(self.transaction)
        self.controller.execute()

        response = self.controller.getresponse()

        if response.messages.resultCode == apicontractsv1.messageTypeEnum.Ok:
            return response.transaction
