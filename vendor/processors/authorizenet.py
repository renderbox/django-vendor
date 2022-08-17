"""
Payment processor for Authorize.net.
"""
import ast
import logging

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import IntegerChoices
from django.utils import timezone
from math import ceil
from vendor.config import VENDOR_PAYMENT_PROCESSOR, VENDOR_STATE
from vendor.utils import get_future_date_days, get_payment_scheduled_end_date
from vendor.integrations import AuthorizeNetIntegration

logger = logging.getLogger(__name__)

try:
    from authorizenet import apicontractsv1
    from authorizenet import constants
    from authorizenet.apicontrollers import *
    import pyxb


    class CustomDate(pyxb.binding.datatypes.date):
        def __new__(cls, *args, **kw):
            # Because of some python, XsdLiteral (pyxb.binding.datatypes)
            # When a new date is created that is not a datetime and those, has more arguments,
            # it requires to only have the year, month and day arguments.

            if len(args) == 8:
                args = args[:3]
            return super().__new__(cls, *args, **kw)
            
except ModuleNotFoundError:
    if VENDOR_PAYMENT_PROCESSOR == "authorizenet.AuthorizeNetProcessor":
        print("WARNING: authorizenet module not found.  Install the library if you want to use the AuthorizeNetProcessor.")
        raise
    pass

from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.models.choice import SubscriptionStatus, TransactionTypes, PaymentTypes, TermType, TermDetailUnits, InvoiceStatus, PurchaseStatus
from vendor.models import Invoice, Payment, Subscription, Receipt, Offer, CustomerProfile
from vendor.models.address import Country
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

    def processor_setup(self, site):
        """
        Merchant Information needed to aprove the transaction.
        """
        self.merchant_auth = apicontractsv1.merchantAuthenticationType()
        self.credentials = AuthorizeNetIntegration(site)

        if self.credentials.instance:
            self.merchant_auth.name = self.credentials.instance.client_id
            self.merchant_auth.transactionKey = self.credentials.instance.public_key
        elif settings.AUTHORIZE_NET_TRANSACTION_KEY and settings.AUTHORIZE_NET_API_ID:
            self.merchant_auth.transactionKey = settings.AUTHORIZE_NET_TRANSACTION_KEY
            self.merchant_auth.name = settings.AUTHORIZE_NET_API_ID
        else:
            logger.error("AuthorizeNetProcessor Missing Authorize.net keys in settings: AUTHORIZE_NET_TRANSACTION_KEY and/or AUTHORIZE_NET_API_ID")
            raise ValueError("Missing Authorize.net keys in settings: AUTHORIZE_NET_TRANSACTION_KEY and/or AUTHORIZE_NET_API_ID")

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

    def create_customer_data_recurring(self):
        customerData = apicontractsv1.customerType()
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
        billing_address.company = self.billing_address.data.get('billing-company', "")[:50]
        address_lines = self.billing_address.data.get('billing-address_1', "")
        if self.billing_address.data['billing-address_2']:
            address_lines += f", {self.billing_address.data['billing-address_2']}"
        billing_address.address = address_lines
        billing_address.city = self.billing_address.data.get("billing-locality", "")[:40]
        billing_address.state = self.billing_address.data.get("billing-state", "")[:40]
        billing_address.zip = self.billing_address.data.get("billing-postal_code")[:20]
        country = Country(int(self.billing_address.data.get("billing-country")))
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
    
    def get_interval_units(self, subscription):
        if subscription.offer.term_details.get('term_units', TermDetailUnits.MONTH) == TermDetailUnits.DAY:
            return apicontractsv1.ARBSubscriptionUnitEnum.days
        return apicontractsv1.ARBSubscriptionUnitEnum.months

    def create_payment_scheduale_interval_type(self, subscription, subscription_type):
        """
        Create an interval schedule with fixed months as units for period length.
        It calculates that start date depending on the term_units and trial_occurrences defined in the term_details.
        term_units can either be by day or by month. Start date is the first billing date of the subscriptions.
        Eg. for a 1 year 1 month free subscription:
            term_unit=20 (Month), trial_occurrences=1
            start_date = now + 1 month
        Eg. for a 7 day free 1 Month subscription:
            term_units=10 (Day), trial_occurrences=7
            start_date = now + 7 days
        """
        payment_schedule = apicontractsv1.paymentScheduleType()
        payment_schedule.interval = apicontractsv1.paymentScheduleTypeInterval()
        payment_schedule.interval.unit = self.get_interval_units(subscription)

        payment_schedule.interval.length = subscription.offer.get_period_length()
        payment_schedule.totalOccurrences = subscription.offer.get_payment_occurrences()
        payment_schedule.startDate = CustomDate(get_future_date_days(timezone.now(), subscription.offer.get_trial_days()))
        payment_schedule.trialOccurrences = subscription.offer.get_trial_occurrences()
        return payment_schedule

    def create_transaction_order_information(self, invoice_number, description):
        order = apicontractsv1.orderType()
        order.invoiceNumber = invoice_number
        order.description = description
        return order

    def create_paging(self, limit, offset=1):
        paging = apicontractsv1.Paging()
        paging.limit = limit
        paging.offset = offset

        return paging

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

    def save_subscription_result(self):
        """
        Processes the transaction reponse from the gateway so it can be saved in the payment model
        The transaction id is the subscription id returned by Authorize.Net
        """
        self.transaction_id = self.transaction_message.get("subscription_id", 'failed_subscription')

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
                        logger.info(f"AuthorizeNetProcessor check_response Failed Transaction: code {self.transaction_message['error_code']}, msg: {self.transaction_message['error_text']}")
            # Or, print errors if the API request wasn't successful
            else:
                self.transaction_message['msg'] = 'Failed Transaction.'
                if hasattr(response, 'transactionResponse') is True and hasattr(response.transactionResponse, 'errors') is True:
                    self.transaction_message['error_code'] = response.transactionResponse.errors.error[0].errorCode
                    self.transaction_message['error_text'] = response.transactionResponse.errors.error[0].errorText
                else:
                    self.transaction_message['error_code'] = response.messages.message[0]['code'].text
                    self.transaction_message['error_text'] = response.messages.message[0]['text'].text
                logger.info(f"AuthorizeNetProcessor check_response Failed Transaction: code {self.transaction_message['error_code']}, msg: {self.transaction_message['error_text']}")
        else:
            logger.info("AuthorizeNetProcessor check_response Null Response")
            self.transaction_message['msg'] = 'Null Response.'

    def check_subscription_response(self, response):
        self.transaction_response = response
        self.transaction_message = {}
        self.transaction_submitted = False
        self.transaction_message['msg'] = ""
        self.transaction_message['code'] = response.messages.message[0]['code'].text
        self.transaction_message['message'] = response.messages.message[0]['text'].text

        if (response.messages.resultCode == "Ok"):
            self.transaction_submitted = True
            self.transaction_message['msg'] = "Subscription Tansaction Complete"
            if 'subscriptionId' in response.__dict__:
                self.transaction_message['subscription_id'] = response.subscriptionId.text
        
        logger.info(f"AuthorizeNetProcessor check_subscription_response submitted: {self.transaction_submitted} msg: {self.transaction_message}")

    def check_customer_list_response(self, response):
        self.transaction_response = response
        self.transaction_message = {}
        self.transaction_submitted = False
        self.transaction_message['msg'] = ""
        self.transaction_message['code'] = response.messages.message[0]['code'].text
        self.transaction_message['message'] = response.messages.message[0]['text'].text

        if (response.messages.resultCode == "Ok"):
            self.transaction_submitted = True

    def to_valid_decimal(self, number):
        # TODO: Need to check currency to determin decimal places.
        return Decimal(number).quantize(Decimal('.00'))

    ##########
    # Base Processor Transaction Implementations
    ##########
    def process_payment(self):
        # Init transaction
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(settings.AUTHORIZE_NET_TRANSACTION_TYPE_DEFAULT)
        self.transaction_type.amount = self.to_valid_decimal(self.invoice.get_one_time_transaction_total())
        self.transaction_type.payment = self.create_authorize_payment()
        self.transaction_type.customer = self.create_customer_data()
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

        if self.transaction_submitted:
            self.payment.status = PurchaseStatus.CAPTURED
        else:
            self.payment.status = PurchaseStatus.DECLINED

        self.payment.save()

    def subscription_payment(self, subscription):
        """
        subscription: Type: OrderItem
        Creates a subscription for a user. Subscriptions can be monthy or yearly.objects.all()
        """
        # Setting subscription details
        self.transaction_type = apicontractsv1.ARBSubscriptionType()
        self.transaction_type.name = subscription.offer.name
        self.transaction_type.paymentSchedule = self.create_payment_scheduale_interval_type(subscription, subscription.offer.terms)
        self.transaction_type.amount = self.to_valid_decimal(subscription.total - subscription.discounts)
        self.transaction_type.trialAmount = self.to_valid_decimal(subscription.offer.get_trial_amount())
        self.transaction_type.billTo = self.create_billing_address(apicontractsv1.nameAndAddressType())
        self.transaction_type.payment = self.create_authorize_payment()
        self.transaction_type.customer = self.create_customer_data_recurring()

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

        self.save_subscription_result()

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

    def subscription_cancel(self, subscription):
        """
        If receipt.invoice.total is zero, no need to call Gateway as there is no
        transaction for it. Otherwise it will cancel the subscription on the Gateway
        and if successfull it will cancel it on the receipt.
        """
        self.transaction = apicontractsv1.ARBCancelSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(subscription.gateway_id)
        self.transaction.includeTransactions = False

        self.controller = ARBCancelSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()

        self.check_subscription_response(response)

        if self.transaction_submitted:
            super().subscription_cancel(subscription)

    def subscription_info(self, subscription_id):
        self.transaction = apicontractsv1.ARBGetSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(subscription_id)
        self.transaction.includeTransactions = True

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
            payment.status = PurchaseStatus.REFUNDED
            payment.save()

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

        super().void_payment()

    def is_card_valid(self):
        """
        Handles an Authorize Only transaction to ensure that the funds are in the customers bank account
        """
        invoice_number = str(self.invoice.pk)[:19]
        description = "This amount is only to check for valid cards and will not be charged. Depending on your bank the charge can take 3 to 5 days to be removed."
        self.create_payment_model(settings.VENDOR_CHARGE_VALIDATION_PRICE)
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(self.transaction_types[TransactionTypes.AUTHORIZE])
        self.transaction_type.amount = self.to_valid_decimal(settings.VENDOR_CHARGE_VALIDATION_PRICE)
        self.transaction_type.payment = self.create_authorize_payment()
        self.transaction_type.billTo = self.create_billing_address(apicontractsv1.customerAddressType())
        self.transaction_type.order = self.create_transaction_order_information(invoice_number, description)
        
        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        # You execute and get the response
        response = self.controller.getresponse()
        self.check_response(response)

        if self.transaction_submitted:
            self.payment.transaction = self.transaction_message['trans_id'].text
            self.payment.save()
            self.void_payment(self.transaction_message['trans_id'].text)
            return True
        return False

    def subscription_update_price(self, receipt, new_price, user):
        self.transaction_type = apicontractsv1.ARBSubscriptionType()
        self.transaction_type.amount = self.to_valid_decimal(new_price)

        self.transaction = apicontractsv1.ARBUpdateSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(receipt.transaction)
        self.transaction.subscription = self.transaction_type

        self.controller = ARBUpdateSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        response = self.controller.getresponse()

        self.check_subscription_response(response)

        if self.transaction_submitted:
            super().subscription_update_price(receipt, new_price, user)

    def get_customer_id_for_expiring_cards(self, month):
        paging = apicontractsv1.Paging()
        paging.limit = 10
        paging.offset = 1

        sorting = apicontractsv1.CustomerPaymentProfileSorting()
        sorting.orderBy = apicontractsv1.CustomerPaymentProfileOrderFieldEnum.id
        sorting.orderDescending = "false"

        self.transaction = apicontractsv1.getCustomerPaymentProfileListRequest()
        self.transaction.merchantAuthentication = self.merchant_auth

        self.transaction.searchType = apicontractsv1.CustomerPaymentProfileSearchTypeEnum.cardsExpiringInMonth
        self.transaction.month = month
        self.transaction.sorting = sorting
        self.transaction.paging = paging

        self.controller = getCustomerPaymentProfileListController(self.transaction)
        self.controller.execute()

        response = self.controller.getresponse()

        self.check_customer_list_response(response)
        customer_profile_ids = []
        last_page = 1
        
        if self.transaction_submitted and response.paymentProfiles:
            last_page = ceil(response.totalNumInResultSet.pyval / paging.limit)
            customer_profile_ids.extend([customer_profile.customerProfileId.text for customer_profile in response.paymentProfiles.paymentProfile])

        for previous_page in range(1, last_page):
            paging.offset = previous_page + 1
            self.transaction.paging = paging
            self.controller = getCustomerPaymentProfileListController(self.transaction)
            self.controller.execute()
            response = self.controller.getresponse()
            self.check_customer_list_response(response)
            if self.transaction_submitted and response.paymentProfiles:
                customer_profile_ids.extend([customer_profile.customerProfileId.text for customer_profile in response.paymentProfiles.paymentProfile])

        return customer_profile_ids
    
    def get_customer_email(self, customer_id):
        self.transaction = apicontractsv1.getCustomerProfileRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.customerProfileId = customer_id

        self.controller = getCustomerProfileController(self.transaction)
        self.controller.execute()

        response = self.controller.getresponse()

        self.check_customer_list_response(response)

        if self.transaction_submitted:
            return response.profile.email.pyval
        
        return None

    def get_settled_transactions(self, start_date, end_date):
        batch_list = self.get_settled_batch_list(start_date, end_date)
        successfull_transactions = []
        if not batch_list:
            return []
        
        for batch in batch_list:
            transaction_list = self.get_transaction_batch_list(str(batch.batchId))
            successfull_transactions.extend([ transaction for transaction in transaction_list if transaction['transactionStatus'] == 'settledSuccessfully' ])

        return successfull_transactions
    
    def update_payments_to_settled(self, site, settled_transactions):
        for settled_transaction in settled_transactions:
            try:
                payment = Payment.objects.get(profile__site=site, transaction=settled_transaction.transId.text)
                payment.status = PurchaseStatus.SETTLED
                payment.submitted_date = settled_transaction.submitTimeUTC.pyval
                payment.save()
            except ObjectDoesNotExist as exce:
                logger.error(f"update_payments_to_settled payment for transaction: {settled_transaction.transId.text} was not found for site: {site}")

        

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

    def get_list_of_subscriptions(self, limit=1000, offset=1):
        self.transaction = apicontractsv1.ARBGetSubscriptionListRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.searchType = apicontractsv1.ARBGetSubscriptionListSearchTypeEnum.subscriptionActive
        self.transaction.paging = self.create_paging(limit, offset)

        self.controller = ARBGetSubscriptionListController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        # Work on the response
        response = self.controller.getresponse()

        self.check_subscription_response(response)

        if self.transaction_submitted:
            return self.transaction_response.subscriptionDetails.subscriptionDetail
        else:
            return []



def sync_subscriptions_and_create_missing_receipts(site):
    logger.info("sync_subscriptions_and_create_missing_receipts Starting Subscription Migration")
    processor = AuthorizeNetProcessor(site)
    
    subscriptions = processor.get_list_of_subscriptions(1000)
    active_subscription_ids = [ subscription.id.text for subscription in subscriptions if subscription['status'] == 'active' ]
    
    for subscription_id in active_subscription_ids:
        try:
            subscription = Subscription.objects.get(gateway_id=subscription_id, profile__site=site)

        except ObjectDoesNotExist as exce:
            pass

        except Exception as exce:
            pass

        subscription_info = processor.subscription_info(subscription_id)
        # valid_subscription_transactions = [transaction for transaction in subscription_info.subscription.arbTransactions.arbTransaction if hasattr(transaction, 'transId') ]
        valid_subscription_transactions = []
        if hasattr(subscription_info.subscription, 'arbTransactions'):
            for transaction in subscription_info.subscription.arbTransactions.arbTransaction:
                if hasattr(transaction, 'transId'):
                    valid_subscription_transactions.append(transaction)

        for transaction in valid_subscription_transactions:
            logger.info(f"sync_subscriptions_and_create_missing_receipts Processing transaction {transaction}")

            transaction_id = transaction.transId.text

            if not subscription.payments.filter(transaction=transaction_id).count():
                trans_processor = AuthorizeNetProcessor(site)

                trans_detail = trans_processor.get_transaction_detail(transaction_id)
                submitted_datetime = datetime.strptime(trans_detail.submitTimeUTC.pyval, '%Y-%m-%dT%H:%M:%S.%f%z')
                offer = Offer.objects.get(site=site, name=subscription_info.subscription.name)
                
                invoice = Invoice.objects.create(
                    status=InvoiceStatus.COMPLETE,
                    site=site,
                    profile=subscription.profile,
                    ordered_date=submitted_datetime,
                    total=trans_detail.settleAmount.pyval
                )
                invoice.add_offer(offer)
                invoice.save()

                payment_info = {
                    'account_number': trans_detail.payment.creditCard.cardNumber.text[-4:],
                    'account_type': trans_detail.payment.creditCard.cardType.text,
                    'full_name': " ".join([trans_detail.billTo.firstName.text, trans_detail.billTo.lastName.text]),
                    'transaction_id': transaction_id,
                    'subscription_id': trans_detail.subscription.id.text,
                    'payment_number': trans_detail.subscription.payNum.text
                }

                # Create Payment
                payment = Payment(profile=invoice.profile,
                            amount=invoice.total,
                            invoice=invoice,
                            created=submitted_datetime)
                payment.result = payment_info
                payment.subscription = subscription
                payment.success = True
                payment.status = PurchaseStatus.SETTLED
                payment.transaction = transaction_id
                payment.payee_full_name = payment_info['full_name']
                payment.amount = trans_detail.settleAmount.pyval
                payment.submitted_date = trans_detail.submitTimeUTC.pyval
                payment.save()

                # Create Receipt
                receipt = Receipt()
                receipt.profile = invoice.profile
                receipt.order_item = invoice.order_items.first()
                receipt.transaction = payment.transaction
                receipt.meta.update(payment.result)
                receipt.meta['payment_amount'] = payment.amount
                receipt.start_date = submitted_datetime
                receipt.save()

                receipt.products.add(offer.products.first())
                receipt.end_date = get_payment_scheduled_end_date(offer, start_date=receipt.start_date)
                receipt.subscription = subscription
                receipt.save()
    


def create_subscription_model_form_past_receipts(site):
    logger.info("create_subscription_model_form_past_receipts Starting Subscription Migration")
    processor = AuthorizeNetProcessor(site)

    subscriptions = processor.get_list_of_subscriptions(1000)
    active_subscriptions = [ s for s in subscriptions if s['status'] == 'active' ]
    
    create_subscriptions = [sub.id.text for sub in active_subscriptions if not Subscription.objects.filter(profile__site=site, gateway_id=sub.id.text).count() ]
    logger.info(f"create_subscription_model_form_past_receipts Create Subscriptions: {[sub for sub in create_subscriptions]}")

    for sub_detail in create_subscriptions:
        logger.info(f"create_subscription_model_form_past_receipts Starting Migration for Subscription: {sub_detail}")
        subscription_id = sub_detail
        past_receipt = Receipt.objects.filter(transaction=subscription_id).first()
        
        if past_receipt:
            logger.info(f"create_subscription_model_form_past_receipts Deleting Receipts: {Receipt.objects.filter(transaction=subscription_id)}")
            Receipt.objects.filter(transaction=subscription_id).update(deleted=True)
            logger.info(f"create_subscription_model_form_past_receipts Deleting Payments: {Payment.objects.filter(transaction=subscription_id)}")
            Payment.objects.filter(transaction=subscription_id).update(deleted=True)
            logger.info(f"create_subscription_model_form_past_receipts Deleting Invoices: {Invoice.objects.filter(payments__in=Payment.objects.filter(transaction=subscription_id))}")
            Invoice.objects.filter(payments__in=Payment.objects.filter(transaction=subscription_id)).update(deleted=True)
            
            subscription, created = Subscription.objects.get_or_create(
                gateway_id=subscription_id,
                profile=past_receipt.profile
            )
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.auto_renew = True
            subscription.save()
            logger.info(f"create_subscription_model_form_past_receipts Created subscription: {subscription}")
            
            subscription_info = processor.subscription_info(subscription_id)

            for transaction in subscription_info.subscription.arbTransactions.arbTransaction:
                logger.info(f"create_subscription_model_form_past_receipts Processing transaction {transaction}")
                try:
                    transaction_id = transaction.transId.text

                    trans_processor = AuthorizeNetProcessor(site)

                    trans_detail = trans_processor.get_transaction_detail(transaction_id)
                    submitted_datetime = datetime.strptime(trans_detail.submitTimeUTC.pyval, '%Y-%m-%dT%H:%M:%S.%f%z')

                    invoice = Invoice.objects.create(
                        status=InvoiceStatus.COMPLETE,
                        site=past_receipt.profile.site,
                        profile=past_receipt.profile,
                        ordered_date=submitted_datetime,
                        total=trans_detail.settleAmount.pyval
                    )
                    invoice.add_offer(past_receipt.order_item.offer)
                    invoice.save()

                    payment_info = {
                        'account_number': trans_detail.payment.creditCard.cardNumber.text[-4:],
                        'account_type': trans_detail.payment.creditCard.cardType.text,
                        'full_name': " ".join([trans_detail.billTo.firstName.text, trans_detail.billTo.lastName.text]),
                        'transaction_id': transaction_id,
                        'subscription_id': trans_detail.subscription.id.text,
                        'payment_number': trans_detail.subscription.payNum.text
                    }

                    # Create Payment
                    payment = Payment(profile=invoice.profile,
                                amount=invoice.total,
                                invoice=invoice,
                                created=submitted_datetime)
                    payment.result = payment_info
                    payment.subscription = subscription
                    payment.success = True
                    payment.status = PurchaseStatus.SETTLED
                    payment.transaction = transaction_id
                    payment.payee_full_name = payment_info['full_name']
                    payment.amount = trans_detail.settleAmount.pyval
                    payment.submitted_date = trans_detail.submitTimeUTC.pyval
                    payment.save()

                    # Create Receipt
                    receipt = Receipt()
                    receipt.profile = invoice.profile
                    receipt.order_item = past_receipt.order_item
                    receipt.transaction = payment.transaction
                    receipt.meta.update(payment.result)
                    receipt.meta['payment_amount'] = payment.amount
                    receipt.start_date = submitted_datetime
                    receipt.save()

                    receipt.products.add(past_receipt.products.first())
                    receipt.end_date = get_payment_scheduled_end_date(past_receipt.order_item.offer, start_date=receipt.start_date)
                    receipt.subscription = subscription
                    receipt.save()
                except Exception as exce:
                    logger.info(f"create_subscription_model_form_past_receipts Invalid Transaction: {exce}")

        else:
            subscription_info = processor.subscription_info(subscription_id)

            try:
                profile = CustomerProfile.objects.get(site=site, user__email=subscription_info.subscription.profile.email.text)
                offer = Offer.objects.get(site=site, name=subscription_info.subscription.name)


                subscription, created = Subscription.objects.get_or_create(
                    gateway_id=subscription_id,
                    profile=profile
                )
                if subscription_info.subscription.status.text == 'active':
                    subscription.status = SubscriptionStatus.ACTIVE
                subscription.auto_renew = True
                subscription.save()
            
                for transaction in subscription_info.subscription.arbTransactions.arbTransaction:
                    logger.info(f"create_subscription_model_form_past_receipts Processing transaction {transaction}")
                    transaction_id = transaction.transId.text

                    trans_processor = AuthorizeNetProcessor(site)

                    trans_detail = trans_processor.get_transaction_detail(transaction_id)
                    submitted_datetime = datetime.strptime(trans_detail.submitTimeUTC.pyval, '%Y-%m-%dT%H:%M:%S.%f%z')

                    invoice = Invoice.objects.create(
                        status=InvoiceStatus.COMPLETE,
                        site=site,
                        profile=profile,
                        ordered_date=submitted_datetime,
                        total=trans_detail.settleAmount.pyval
                    )
                    invoice.add_offer(offer)
                    invoice.save()

                    payment_info = {
                        'account_number': trans_detail.payment.creditCard.cardNumber.text[-4:],
                        'account_type': trans_detail.payment.creditCard.cardType.text,
                        'full_name': " ".join([trans_detail.billTo.firstName.text, trans_detail.billTo.lastName.text]),
                        'transaction_id': transaction_id,
                        'subscription_id': trans_detail.subscription.id.text,
                        'payment_number': trans_detail.subscription.payNum.text
                    }

                    # Create Payment
                    payment = Payment(profile=invoice.profile,
                                amount=invoice.total,
                                invoice=invoice,
                                created=submitted_datetime)
                    payment.result = payment_info
                    payment.subscription = subscription
                    payment.success = True
                    payment.status = PurchaseStatus.SETTLED
                    payment.transaction = transaction_id
                    payment.payee_full_name = payment_info['full_name']
                    payment.amount = trans_detail.settleAmount.pyval
                    payment.submitted_date = trans_detail.submitTimeUTC.pyval
                    payment.save()

                    # Create Receipt
                    receipt = Receipt()
                    receipt.profile = invoice.profile
                    receipt.order_item = invoice.order_items.first()
                    receipt.transaction = payment.transaction
                    receipt.meta.update(payment.result)
                    receipt.meta['payment_amount'] = payment.amount
                    receipt.start_date = submitted_datetime
                    receipt.save()

                    receipt.products.add(offer.products.first())
                    receipt.end_date = get_payment_scheduled_end_date(offer, start_date=receipt.start_date)
                    receipt.subscription = subscription
                    receipt.save()
            except Exception as exce:
                logger.info(f"create_subscription_model_form_past_receipts Invalid Transaction: {exce} subscription id: {subscription_id}")