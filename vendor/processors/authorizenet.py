"""
Payment processor for Authorize.net.
"""
import ast
from decimal import Decimal, ROUND_DOWN

from django.conf import settings
from django.utils import timezone

from vendor.config import VENDOR_PAYMENT_PROCESSOR, VENDOR_STATE

try:
    from authorizenet import apicontractsv1
    from authorizenet import constants
    from authorizenet.apicontrollers import *
except ModuleNotFoundError:
    if VENDOR_PAYMENT_PROCESSOR == "authorizenet.AuthorizeNetProcessor":
        print("WARNING: authorizenet module not found.  Install the library if you want to use the AuthorizeNetProcessor.")
        raise
    pass

from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.models.choice import TransactionTypes, PaymentTypes, TermType, PurchaseStatus
from vendor.models.invoice import Invoice
from vendor.models.address import Country
from vendor.models.payment import Payment
from .base import PaymentProcessorBase

class AuthorizeNetProcessor(PaymentProcessorBase):
    """
    Implementation of AUTHORIZE.Net SDK
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
        if 'credit_card_form' not in context:
            context['credit_card_form'] = CreditCardForm(initial={'payment_type': PaymentTypes.CREDIT_CARD})
        if 'billing_address_form' not in context:
            context['billing_address_form'] = BillingAddressForm()
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
            TransactionTypes.VOID: self.VOID,
        }

    def init_payment_type_switch(self):
        """
        Initializes the Payment Types create functions
        """
        self.payment_type_switch = {
            PaymentTypes.CREDIT_CARD: self.create_credit_card_payment,
            PaymentTypes.BANK_ACCOUNT: self.create_bank_account_payment,
            PaymentTypes.PAY_PAL: self.create_pay_pal_payment,
            PaymentTypes.MOBILE: self.create_mobile_payment,
        }
    
    def set_api_endpoint(self):
        """
        Sets the API endpoint for debugging or production.It is dependent on the VENDOR_STATE
        enviornment variable. Default value is DEBUG for the VENDOR_STATE
        """
        if VENDOR_STATE == 'DEBUG':
            self.API_ENDPOINT = constants.SANDBOX
        elif VENDOR_STATE == 'PRODUCTION':
            self.API_ENDPOINT = constants.PRODUCTION

    ##########
    # Authorize.net Object creations
    ##########
    def set_controller_api_endpoint(self):
        """
        Sets the endpoint for the controller to point to test or production.
        self.API_ENDPOINT is set on Processor Initialization
        """
        self.controller.setenvironment(self.API_ENDPOINT)

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
        creditCard.cardNumber = self.payment_info.data.get('card_number')
        creditCard.expirationDate = "-".join([self.payment_info.data.get('expire_year'), self.payment_info.data.get('expire_month')])
        creditCard.cardCode = str(self.payment_info.data.get('cvv_number'))
        return creditCard

    def create_bank_account_payment(self):
        raise NotImplementedError

    def create_pay_pal_payment(self):
        raise NotImplementedError

    def create_mobile_payment(self):
        raise NotImplementedError

    def create_authorize_payment(self):
        """
        Creates a payment instance acording to the billing information captured
        """
        payment = apicontractsv1.paymentType()
        payment.creditCard = self.payment_type_switch[int(
            self.payment_info.data.get('payment_type'))]()
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

    def create_line_item(self, order_item):
        """
        Create a single line order_item (products) that is attached to a line order_item array
        """
        line_item = apicontractsv1.lineItemType()
        line_item.itemId = str(order_item.pk)
        line_item.name = order_item.name[:30]
        line_item.description = str(order_item.offer.description)[:250]
        line_item.quantity = str(order_item.quantity)
        line_item.unitPrice = str(order_item.price)
        return line_item

    def create_line_item_array(self, order_items):
        """
        Creates a list o line order_items(products) that are attached to the transaction type
        """
        line_items = apicontractsv1.ArrayOfLineItem()
        for order_item in order_items:
            line_items.lineItem.append(self.create_line_item(order_item))
        return line_items

    def create_tax(self, tax):
        raise NotImplementedError

    def create_shipping(self, shipping):
        raise NotImplementedError

    def create_billing_address(self, api_address_type):
        """
        Creates Billing address to improve security in transaction
        """
        billing_address = api_address_type
        billing_address.firstName = " ".join(self.payment_info.data.get('full_name', "").split(" ")[:-1])[:50]
        billing_address.lastName = (self.payment_info.data.get('full_name', "").split(" ")[-1])[:50]
        billing_address.company = self.billing_address.data.get('company', "")[:50]
        billing_address.address = ", ".join([self.billing_address.data.get('address_1',""), str(self.billing_address.data.get('address_2', ""))])[:60]
        billing_address.city = self.billing_address.data.get("locality", "")[:40]
        billing_address.state = self.billing_address.data.get("state", "")[:40]
        billing_address.zip = self.billing_address.data.get("postal_code")[:20]
        country = Country(int(self.billing_address.data.get("country")))
        billing_address.country = str(country.name)
        return billing_address

    def create_customer(self):
        raise NotImplementedError

    def create_order_type(self):
        """
        Create Authorize.Net OrderType to add invoice and descriptions to the transaction
        """
        order = apicontractsv1.orderType()
        order.invoiceNumber = str(self.invoice.pk)
        order.description = self.get_transaction_id()

        return order

    def get_payment_occurrences(self, subscription, subscription_type):
        """
        Gets the defined payment ocurrences for a Subscription. It defaults to
        9999 which means it will charge that amount until the customer cancels the subscription. 
        """
        return subscription.offer.term_details.get('payment_occurrences', 9999)

    def get_period_length(self, subscription, subscription_type):
        if subscription_type == TermType.SUBSCRIPTION:
            return subscription.offer.term_details['period_length']
        else:
            return subscription_type - 100

    def create_payment_scheduale_interval_type(self, subscription, subscription_type):
        """
        Create an interval schedule with fixed months as units for period lenght.
        It calculates that start date depending on the term_units and trail_occurrences defined in the term_details.
        term_units can either be by day or by month. Start date is the first billing date of the subscriptions.
        Eg. for a 1 year 1 month free subscription:
            term_unit=20 (Month), trail_occurrences=1
            start_date = now + 1 month
        Eg. for a 7 day free 1 Month subscription:
            term_units=10 (Day), trail_occurrences=7
            start_date = now + 7 days
        """
        payment_schedule = apicontractsv1.paymentScheduleType()
        payment_schedule.interval = apicontractsv1.paymentScheduleTypeInterval()
        payment_schedule.interval.unit = apicontractsv1.ARBSubscriptionUnitEnum.months

        payment_schedule.interval.length = self.get_period_length(subscription, subscription_type)
        payment_schedule.totalOccurrences = self.get_payment_occurrences(subscription, subscription_type)
        payment_schedule.startDate = self.get_payment_schedule_start_date(subscription)
        # Authorize.Net does not have a way to differenciate trail occurrences term_units for period length.
        # Set to zero as the start date takes into account the trail occurrences.
        payment_schedule.trialOccurrences = 0
        return payment_schedule

    ##########
    # Django-Vendor to Authoriaze.net data exchange functions
    ##########
    def get_transaction_raw_response(self):
        """
        Returns a dictionary with raw information about the current transaction
        """
        response = self.transaction_response.__dict__
        if 'errors' in response:
            response.pop('errors')
        if 'messages' in response:
            response.pop('messages')
        return str({**self.transaction_message, **response})

    def process_payment_transaction_response(self):
        """
        Processes the transaction reponse from the gateway so it can be saved in the payment model
        """
        self.transaction_id = str(getattr(self.transaction_response, 'transId', 'failed_payment'))

        transaction_info = {}
        transaction_info['raw'] = self.get_transaction_raw_response()
        transaction_info['account_type'] = ast.literal_eval(transaction_info['raw']).get('accountType')

        self.transaction_response = transaction_info

    def save_payment_subscription(self):
        """
        Processes the transaction reponse from the gateway so it can be saved in the payment model
        The transaction id is the subscription id returned by Authorize.Net
        """
        self.transaction_id = self.transaction_message.get("subscription_id", 'failed_payement')

        transaction_info = {}
        transaction_info['raw'] = self.get_transaction_raw_response()

        self.transaction_response = transaction_info

    def check_response(self, response):
        """
        Checks the transaction response and set the transaction_submitted and transaction_response variables
        """
        self.transaction_response = response.transactionResponse
        self.transaction_message = {}
        self.transaction_submitted = False
        self.transaction_message['msg'] = ""
        if response is not None:
            # Check to see if the API request was successfully received and acted upon
            if response.messages.resultCode == "Ok":
                # Since the API request was successful, look for a transaction response
                # and parse it to display the results of authorizing the card
                if hasattr(response.transactionResponse, 'messages') is True:
                    self.transaction_submitted = True
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
    
    def check_subscription_response(self, response):
        self.transaction_response = response
        self.transaction_message = {}
        self.transaction_submitted = False
        self.transaction_message['msg'] = ""
        self.transaction_message['code'] = response.messages.message[0]['code'].text
        self.transaction_message['message'] = response.messages.message[0]['text'].text

        if (response.messages.resultCode=="Ok"):
            self.transaction_submitted = True
            self.transaction_message['msg'] = "Subscription Tansaction Complete"
            if 'subscriptionId' in response.__dict__:
                self.transaction_message['subscription_id'] = response.subscriptionId.text

    def to_valid_decimal(self, number):
        # TODO: Need to check currency to determin decimal places.
        return Decimal(number).quantize(Decimal('.00'), rounding=ROUND_DOWN)
    ##########
    # Base Processor Transaction Implementations
    ##########
    def process_payment(self):
        # Init transaction
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(settings.AUTHORIZE_NET_TRANSACTION_TYPE_DEFAULT)
        self.transaction_type.amount = self.to_valid_decimal(self.invoice.get_one_time_transaction_total())
        self.transaction_type.payment = self.create_authorize_payment()
        self.transaction_type.billTo = self.create_billing_address(apicontractsv1.customerAddressType())

        # Optional items for make it easier to read and use on the Authorize.net portal.
        if self.invoice.order_items:
            self.transaction_type.lineItems = self.create_line_item_array(self.invoice.order_items.all())

        # You set the request to the transaction
        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        # You execute and get the response
        response = self.controller.getresponse()
        self.check_response(response)

        self.process_payment_transaction_response()
    
    def subscription_payment(self, subscription):
        """
        subscription: Type: OrderItem
        Creates a subscription for a user. Subscriptions can be monthy or yearly.objects.all()
        """
        # Setting subscription details
        self.transaction_type = apicontractsv1.ARBSubscriptionType()
        self.transaction_type.name = subscription.offer.name
        self.transaction_type.paymentSchedule = self.create_payment_scheduale_interval_type(subscription, subscription.offer.terms)
        self.transaction_type.amount = self.to_valid_decimal(subscription.total)
        self.transaction_type.trialAmount = Decimal('0.00')
        self.transaction_type.billTo = self.create_billing_address(apicontractsv1.nameAndAddressType())
        self.transaction_type.payment = self.create_authorize_payment()

        # Optional to add Order information. 
        self.transaction_type.order = self.create_order_type()

        # Creating the request
        self.transaction = apicontractsv1.ARBCreateSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscription = self.transaction_type

        # Creating and executing the controller
        self.controller = ARBCreateSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        # Getting the response
        response = self.controller.getresponse()
        self.check_subscription_response(response)

        self.save_payment_subscription()

    def subscription_update_payment(self, receipt):
        """
        Updates the credit card information for the subscriptions in authorize.net 
        and updates the payment record associated with the receipt.
        """
        self.payment = Payment.objects.get(success=True, transaction=receipt.transaction, invoice=receipt.order_item.invoice)

        self.transaction_type = apicontractsv1.ARBSubscriptionType()
        self.transaction_type.payment = self.create_authorize_payment()

        self.transaction = apicontractsv1.ARBUpdateSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(receipt.transaction)
        self.transaction.subscription = self.transaction_type

        self.controller = ARBUpdateSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()

        self.check_subscription_response(response)

        receipt.meta[f"payment-update-{timezone.now():%Y-%m-%d %H:%M}"] = {'raw': str({**self.transaction_message, **response})}
        receipt.save()

        subscription_info = self.subscription_info(receipt.transaction)

        account_number = getattr(subscription_info['subscription']['profile']['paymentProfile']['payment']['creditCard'], 'cardNumber', None)
        if account_number:
            self.payment.result['account_number'] = account_number.text
            
        account_type = getattr(subscription_info['subscription']['profile']['paymentProfile']['payment']['creditCard'], 'accountType', None)
        if account_type:
            self.payment.result['account_type'] = account_type.text
        
        self.payment.save()

    def subscription_cancel(self, receipt):
        self.transaction = apicontractsv1.ARBCancelSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(receipt.transaction)
        self.transaction.includeTransactions = False

        self.controller = ARBCancelSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()

        self.check_subscription_response(response)

        if self.transaction_submitted:
            receipt.status = PurchaseStatus.CANCELED
            receipt.auto_renew = False
            receipt.save()

    def subscription_info(self, subscription_id):
        self.transaction = apicontractsv1.ARBGetSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(subscription_id)
        self.transaction.includeTransactions = False

        self.controller = ARBGetSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()

        return response

    def refund_payment(self, payment):
        # Init transaction
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(
            self.transaction_types[TransactionTypes.REFUND])
        self.transaction_type.amount = self.to_valid_decimal(payment.amount)
        self.transaction_type.refTransId = payment.transaction

        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = ast.literal_eval(payment.result['raw']).get('accountNumber')[-4:]
        creditCard.expirationDate = "XXXX"

        payment_type = apicontractsv1.paymentType()
        payment_type.creditCard = creditCard
        self.transaction_type.payment = payment_type

        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()
        self.check_response(response)

        if self.transaction_submitted:
            self.update_invoice_status(Invoice.InvoiceStatus.REFUNDED)

    def void_payment(self, transaction_id):
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(self.transaction_types[TransactionTypes.VOID])
        self.transaction_type.refTransId = transaction_id

        self.transaction.transactionRequest = self.transaction_type

        self.controller = createTransactionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()

        self.check_response(response)

    def is_card_valid(self):
        """
        Handles an Authorize Only transaction to ensure that the funds are in the customers bank account
        """
        self.create_payment_model()
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(self.transaction_types[TransactionTypes.AUTHORIZE])
        self.transaction_type.amount = self.to_valid_decimal(self.invoice.get_recurring_total())
        self.transaction_type.payment = self.create_authorize_payment()
        self.transaction_type.billTo = self.create_billing_address(apicontractsv1.customerAddressType())

        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        # You execute and get the response
        response = self.controller.getresponse()
        self.check_response(response)

        if self.transaction_submitted:
            self.void_payment(self.transaction_message['trans_id'].text)
            return True
        return False

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
        self.set_controller_api_endpoint()
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
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()

        if response.messages.resultCode == apicontractsv1.messageTypeEnum.Ok and hasattr(response, 'transactions'):
            return [transaction for transaction in response.transactions.transaction]

    def get_transaction_detail(self, transaction_id):
        self.transaction = apicontractsv1.getTransactionDetailsRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.transId = transaction_id

        self.controller = getTransactionDetailsController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()

        if response.messages.resultCode == apicontractsv1.messageTypeEnum.Ok:
            return response.transaction

    def get_list_of_subscriptions(self):
        self.transaction = apicontractsv1.ARBGetSubscriptionListRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.searchType = apicontractsv1.ARBGetSubscriptionListSearchTypeEnum.subscriptionActive

        self.controller = ARBGetSubscriptionListController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        # Work on the response
        response = self.controller.getresponse()
        if response.messages.resultCode == apicontractsv1.messageTypeEnum.Ok and hasattr(response.subscriptionDetails, 'subscriptionDetail'):
            return response.subscriptionDetails.subscriptionDetail
        else:
            return []


