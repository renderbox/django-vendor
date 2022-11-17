"""
Payment processor for Authorize.net.
"""
import ast
import logging

from datetime import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
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
    subscription_details = []

    def __str__(self):
        return 'Authorize.Net'


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
        transaction.refId = self.get_transaction_id()[:20]
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
        subscription: Type: OrderItem
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
        start_date = subscription.offer.get_term_start_date()

        payment_schedule = apicontractsv1.paymentScheduleType()
        payment_schedule.interval = apicontractsv1.paymentScheduleTypeInterval()
        payment_schedule.interval.unit = self.get_interval_units(subscription)

        payment_schedule.interval.length = subscription.offer.get_period_length()
        payment_schedule.totalOccurrences = subscription.offer.get_payment_occurrences()

        if self.invoice.profile.has_owned_product(subscription.offer.products.all()):
            payment_schedule.startDate = CustomDate(start_date)
            payment_schedule.trialOccurrences = 0
        else:
            payment_schedule.startDate = CustomDate(get_future_date_days(start_date, subscription.offer.get_trial_days()))
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
    def get_payment_success(self, response_code):
        if response_code == "1":
            return True
        
        return False

    def get_payment_status(self, transaction_status):
        if transaction_status == 'authorizedPendingCapture':
            return PurchaseStatus.AUTHORIZED
        elif transaction_status == 'capturedPendingSettlement':
            return PurchaseStatus.CAPTURED
        elif transaction_status == 'communicationError':
            return PurchaseStatus.ERROR
        elif transaction_status == 'refundSettledSuccessfully':
            return PurchaseStatus.REFUNDED
        elif transaction_status == 'approvedReview':
            return PurchaseStatus.AUTHORIZED
        elif transaction_status == 'declined':
            return PurchaseStatus.DECLINED
        elif transaction_status == 'couldNotVoid':
            return PurchaseStatus.ERROR
        elif transaction_status == 'expired':
            return PurchaseStatus.DECLINED
        elif transaction_status == 'generalError':
            return PurchaseStatus.ERROR
        elif transaction_status == 'failedReview':
            return PurchaseStatus.ERROR
        elif transaction_status == 'settledSuccessfully':
            return PurchaseStatus.SETTLED
        elif transaction_status == 'settlementError':
            return PurchaseStatus.ERROR
        elif transaction_status == 'underReview':
            return PurchaseStatus.ERROR
        elif transaction_status == 'voided':
            return PurchaseStatus.VOID
        elif transaction_status == 'FDSPendingReview':
            return PurchaseStatus.ERROR
        elif transaction_status == 'FDSAuthorizedPendingReview':
            return PurchaseStatus.ERROR
        elif transaction_status == 'returnedItem':
            return PurchaseStatus.REFUNDED
        else:
            raise TypeError(f"{transaction_status} is not supported, check Authorize.Net docs for transactionStatus field choices")

    def get_payment_info(self, transaction):
        account_number = transaction.payment.creditCard.cardNumber.text[-4:]
        full_name = " ".join([transaction.billTo.firstName.text, transaction.billTo.lastName.text])

        payment_info = super().get_payment_info(account_number, full_name)
        
        return payment_info.update({
            'account_type': transaction.payment.creditCard.cardType.text,
            'transaction_id': transaction.transId.text,
            'subscription_id': transaction.subscription.id.text if hasattr(transaction, 'subscription') else "-",
            'payment_number': transaction.subscription.payNum.text,
            'status': transaction.transactionStatus.text
        })

    def subscription_info_to_dict(self, subscription_info):
        return {
            'name': subscription_info.subscription.name.text,
            'interval': subscription_info.subscription.paymentSchedule.interval.length.text,
            'unit': subscription_info.subscription.paymentSchedule.interval.unit.text,
            'start_date': subscription_info.subscription.paymentSchedule.startDate.text,
            'total_occurrences': subscription_info.subscription.paymentSchedule.totalOccurrences.text,
            'trial_occurrences': subscription_info.subscription.paymentSchedule.trialOccurrences.text,
            'amount': subscription_info.subscription.amount.text,
            'trial_amount': subscription_info.subscription.trialAmount.text,
        }

    def get_vendor_subscription_status(self, subscription_status):
        if subscription_status == 'active':
            return SubscriptionStatus.ACTIVE
        elif subscription_status == 'expired':
            return SubscriptionStatus.EXPIRED
        elif subscription_status == 'suspended':
            return SubscriptionStatus.SUSPENDED
        elif subscription_status == 'canceled':
            return SubscriptionStatus.CANCELED
        elif subscription_status == 'terminated':
            return SubscriptionStatus.SUSPENDED
        else:
            raise TypeError(f"{subscription_status} status is not valid, take a look at Authorize.Net documentation")

    def get_transaction_raw_response(self):
        """
        Returns a dictionary with raw information about the current transaction
        """
        response = self.transaction_response.__dict__

        if 'errors' in response:
            response.pop('errors')

        if 'messages' in response:
            response.pop('messages')
            
        return str({**self.transaction_info, **response})

    def get_transaction_errors(self, transaction_data=None):
        errors = []

        if self.transaction_response.messages.resultCode == "Error":
            errors.append({key: value.text for key, value in self.transaction_response.messages.message.__dict__.items() if value.text})

        if transaction_data and hasattr(transaction_data, 'errors'):
            errors.append({key: value.text for key, value in transaction_data.errors.error.__dict__.items() if value.text})
        
        return errors

    def get_transaction_data(self, transaction_data=None):
        response_data = {key: value.text for key, value in self.transaction_response.__dict__.items() if value.text}

        if transaction_data:
            for key, value in transaction_data.__dict__.items():
                if value.text:
                    response_data.update({key: value.text})

        if 'messages' in self.transaction_response.__dict__:
            response_data['resultCode'] = self.transaction_response.messages.resultCode.text
            response_data['messages'] = {key: value.text for key, value in self.transaction_response.messages.message.__dict__.items() if value.text}

        return response_data

    def parse_response(self, parser_function):
        """
        Processes the transaction response from the gateway so it can be saved in the payment model
        """
        parser_function()

    def is_transaction_response_empty(self):

        if not self.transaction_response:
            self.set_transaction_info(
                raw="No transaction Response was set",
                errors="No transaction Response was set",
                messages="No transaction Response was set"
            )
            return True
        
        return False

    def parse_payment_response(self):
        self.transaction_info = {}

        if self.is_transaction_response_empty():
            return None

        errors = self.get_transaction_errors(self.transaction_response.transactionResponse)
        
        if not hasattr(self.transaction_response, 'transactionResponse'):
            self.set_transaction_info(
                raw=self.get_transaction_raw_response(),
                errors=errors
            )
            return None

        self.transaction_info = self.get_transaction_info(
            raw=self.get_transaction_raw_response(),
            errors=errors,
            data=self.get_transaction_data(self.transaction_response.transactionResponse)
        )

    def parse_transaction_response(self):
        self.transaction_info = {}

        if self.is_transaction_response_empty():
            return None

        errors = self.get_transaction_errors()

        self.transaction_info = self.get_transaction_info(
            raw=self.get_transaction_raw_response(),
            errors=errors,
            data=self.get_transaction_data()
        )

    def parse_success(self):
        self.transaction_succeeded = False

        if hasattr(self.transaction_response, 'messages') and\
           self.transaction_response.messages.resultCode == "Ok" and\
           not self.transaction_info['errors']:
            self.transaction_succeeded = True

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
        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_payment_response)
        self.parse_success()

        self.transaction_id = self.transaction_info['data'].get('transId', "")

        if self.transaction_succeeded:
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
        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()

        if self.transaction_succeeded:
            self.subscription_id = self.transaction_info['data'].get('subscription_id', "")

    def subscription_update_payment(self, subscription):
        """
        Updates the credit card information for the subscriptions in authorize.net
        and updates the payment record associated with the receipt.
        """
        self.transaction_type = apicontractsv1.ARBSubscriptionType()
        self.transaction_type.payment = self.create_authorize_payment()

        self.transaction = apicontractsv1.ARBUpdateSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = subscription.gateway_id
        self.transaction.subscription = self.transaction_type

        self.controller = ARBUpdateSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()

        subscription_info = self.subscription_info(subscription.gateway_id)

        payment_info = {}
        account_number = getattr(subscription_info['subscription']['profile']['paymentProfile']['payment']['creditCard'], 'cardNumber', None)
        account_type = getattr(subscription_info['subscription']['profile']['paymentProfile']['payment']['creditCard'], 'accountType', None)

        if account_number:
            payment_info['account_number'] = account_number.text

        if account_type:
            payment_info['account_type'] = account_type.text

        subscription.save_payment_info(payment_info)

    def subscription_cancel(self, subscription):
        """
        If receipt.invoice.total is zero, no need to call Gateway as there is no
        transaction for it. Otherwise it will cancel the subscription on the Gateway
        and if successfull it will cancel it on the receipt.
        """
        super().subscription_cancel(subscription)
        
        self.transaction = apicontractsv1.ARBCancelSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(subscription.gateway_id)
        self.transaction.includeTransactions = False

        self.controller = ARBCancelSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()
            
    def subscription_info(self, subscription_id):
        self.transaction = apicontractsv1.ARBGetSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(subscription_id)
        self.transaction.includeTransactions = True

        self.controller = ARBGetSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()
        
        if self.transaction_succeeded:
            return self.transaction_response

        return None

    def refund_payment(self, payment):
        # Init transaction
        self.transaction = self.create_transaction()
        self.transaction_type = self.create_transaction_type(
            self.transaction_types[TransactionTypes.REFUND])
        self.transaction_type.amount = self.to_valid_decimal(payment.amount)
        self.transaction_type.refTransId = payment.transaction

        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = ast.literal_eval(payment.result['payment_info']).get('account_number')[-4:]
        creditCard.expirationDate = "XXXX"

        payment_type = apicontractsv1.paymentType()
        payment_type.creditCard = creditCard
        self.transaction_type.payment = payment_type

        self.transaction.transactionRequest = self.transaction_type
        self.controller = createTransactionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_payment_response)
        self.parse_success()
        
        if self.transaction_succeeded:
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

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_payment_response)
        self.parse_success()
        
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
        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_payment_response)
        self.parse_success()
        
        if self.transaction_succeeded:
            self.payment.transaction = self.transaction_info['data'].get('trans_id', "")
            self.payment.save()
            self.void_payment(self.payment.transaction)

            return True

        return False

    def subscription_update_price(self, subscription, new_price, user):
        self.transaction_type = apicontractsv1.ARBSubscriptionType()
        self.transaction_type.amount = self.to_valid_decimal(new_price)

        self.transaction = apicontractsv1.ARBUpdateSubscriptionRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.subscriptionId = str(subscription.gateway_id)
        self.transaction.subscription = self.transaction_type

        self.controller = ARBUpdateSubscriptionController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()

        if self.transaction_succeeded:
            super().subscription_update_price(subscription, new_price, user)

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

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()

        customer_profile_ids = []
        last_page = 1
        
        if self.transaction_succeeded and self.transaction_response.paymentProfiles:
            last_page = ceil(self.transaction_response.totalNumInResultSet.pyval / paging.limit)
            customer_profile_ids.extend([customer_profile.customerProfileId.text for customer_profile in self.transaction_response.paymentProfiles.paymentProfile])

        for previous_page in range(1, last_page):
            paging.offset = previous_page + 1

            self.transaction.paging = paging
            self.controller = getCustomerPaymentProfileListController(self.transaction)
            self.controller.execute()
            self.transaction_response = self.controller.getresponse()
            self.parse_response(self.parse_transaction_response)
            self.parse_success()

            if self.transaction_succeeded and self.transaction_response.paymentProfiles:
                customer_profile_ids.extend([customer_profile.customerProfileId.text for customer_profile in self.transaction_response.paymentProfiles.paymentProfile])

        return customer_profile_ids
    
    def get_customer_email(self, customer_id):
        self.transaction = apicontractsv1.getCustomerProfileRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.customerProfileId = customer_id

        self.controller = getCustomerProfileController(self.transaction)
        self.controller.execute()

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()

        if self.transaction_succeeded:
            return self.transaction_response.profile.email.pyval
        
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

        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()

        if self.transaction_succeeded and hasattr(self.transaction_response, 'batchList'):
            return [batch for batch in self.transaction_response.batchList.batch]

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

    def get_list_of_subscriptions(self, limit=1000, offset=1, search_type=apicontractsv1.ARBGetSubscriptionListSearchTypeEnum.subscriptionActive):
        self.transaction = apicontractsv1.ARBGetSubscriptionListRequest()
        self.transaction.merchantAuthentication = self.merchant_auth
        self.transaction.searchType = search_type
        self.transaction.paging = self.create_paging(limit, offset)

        self.controller = ARBGetSubscriptionListController(self.transaction)
        self.set_controller_api_endpoint()
        self.controller.execute()

        # Work on the response
        self.transaction_response = self.controller.getresponse()
        self.parse_response(self.parse_transaction_response)
        self.parse_success()

        if self.transaction_succeeded:
            return self.transaction_response.subscriptionDetails.subscriptionDetail
        else:
            return []

    def get_subscription_transactions(self, subscription_info):
        subscription_transactions = []
        if not hasattr(subscription_info.subscription, 'arbTransactions'):
            return []

        for transaction in subscription_info.subscription.arbTransactions.arbTransaction:
            if hasattr(transaction, 'transId'):
                transaction_detail = self.get_transaction_detail(transaction.transId.text)
                subscription_transactions.append(transaction_detail)

        return subscription_transactions


def sync_subscriptions(site):
    logger.info("sync_subscriptions Starting Subscription Migration")
    processor = AuthorizeNetProcessor(site)

    active_subscriptions = processor.get_list_of_subscriptions()
    subscription_ids = [ subscription.id.text for subscription in active_subscriptions ]

    inactive_subscriptions = processor.get_list_of_subscriptions(search_type=apicontractsv1.ARBGetSubscriptionListSearchTypeEnum.subscriptionInactive)
    subscription_ids.extend([ subscription.id.text for subscription in inactive_subscriptions ])
    
    for subscription_id in subscription_ids:
        subscription_info = processor.subscription_info(subscription_id)

        if hasattr(subscription_info.subscription.profile, 'email'):
            email = subscription_info.subscription.profile.email.text

            try:
                customer_profile = CustomerProfile.objects.get(site=site, user__email__iexact=email)
                offers = Offer.objects.filter(site=site, name=subscription_info.subscription.name)

                if not offers.count():
                    raise ObjectDoesNotExist()
                
                offer = offers.first()

                ## Create a subscription with status.
                subscription, _ = Subscription.objects.get_or_create(gateway_id=subscription_id, profile=customer_profile)
                subscription.status = processor.get_vendor_subscription_status(subscription_info.subscription.status.text)
                subscription.meta = processor.subscription_info_to_dict(subscription_info)
                subscription.save()

                ## Get transactions for subscription.
                subscription_transactions = processor.get_subscription_transactions(subscription_info)

                for transaction in subscription_transactions:
                    transaction_id = transaction.transId.text
                    transaction_detail = processor.get_transaction_detail(transaction_id)
                    
                    submitted_datetime = datetime.strptime(transaction_detail.submitTimeUTC.pyval, '%Y-%m-%dT%H:%M:%S.%f%z')
                    payment_info = processor.get_payment_info(transaction_detail)
                    payment_status = processor.get_payment_status(transaction_detail.transactionStatus.text)
                    payment_success = processor.get_payment_success(transaction_detail.responseCode.text)

                    if not subscription.payments.filter(transaction=transaction_id).count():
                        ### Create Invoice
                        invoice = Invoice.objects.create(
                            profile=customer_profile,
                            site=site,
                            ordered_date=submitted_datetime,
                            total=transaction_detail.settleAmount.pyval,
                            status=InvoiceStatus.COMPLETE
                        )
                        invoice.add_offer(offer)
                        invoice.save()

                        ### Create Payment
                        payment = Payment()
                        payment.profile = customer_profile
                        payment.invoice = invoice
                        payment.subscription = subscription
                        payment.amount = transaction_detail.settleAmount.pyval
                        payment.submitted_date = submitted_datetime
                        payment.status = payment_status
                        payment.success = payment_success
                        payment.transaction = transaction_id
                        payment.result = {}

                        if payment_info:
                            payment.result['payment_info'] = payment_info
                            payment.payee_full_name = payment_info.get('full_name', '')

                        payment.save()

                        if payment_status == PurchaseStatus.SETTLED:
                            ### Create Receipt.
                            receipt = Receipt()
                            receipt.profile = customer_profile
                            receipt.order_item = invoice.order_items.first()
                            receipt.start_date = submitted_datetime
                            receipt.end_date = get_payment_scheduled_end_date(offer, start_date=submitted_datetime)
                            receipt.transaction = payment.transaction
                            receipt.subscription = subscription
                            receipt.meta.update(payment.result)
                            receipt.meta['payment_amount'] = payment.amount
                            receipt.save()
                            
                            receipt.products.add(offer.products.first())

                    else:
                        # Update the Payment
                        payment = subscription.payments.get(transaction=transaction_id)
                        payment.amount = transaction_detail.settleAmount.pyval
                        payment.submitted_date = submitted_datetime
                        payment.status = payment_status
                        payment.success = payment_success
                        payment.result = {}

                        if payment_info:
                            payment.result['payment_info'] = payment_info
                            payment.payee_full_name = payment_info.get('full_name', '')
                            
                        payment.save()

                        if not payment.invoice:                        ### Create Invoice
                            invoice = Invoice.objects.create(
                                profile=customer_profile,
                                site=site,
                                ordered_date=submitted_datetime,
                                total=transaction_detail.settleAmount.pyval,
                                status=InvoiceStatus.COMPLETE
                            )
                            invoice.add_offer(offer)
                            invoice.save()
                            
                            payment.invoice = invoice
                            payment.save()
                        else:
                            invoice = payment.invoice

                        if Receipt.objects.filter(deleted=False, transaction=transaction_id, profile=customer_profile).count():
                            receipt = Receipt.objects.get(deleted=False, transaction=transaction_id, profile=customer_profile)
                            
                            if payment.status == PurchaseStatus.SETTLED:
                                receipt.profile = customer_profile
                                receipt.order_item = invoice.order_items.first()
                                receipt.start_date = submitted_datetime
                                receipt.end_date = get_payment_scheduled_end_date(offer, start_date=submitted_datetime)
                                receipt.transaction = payment.transaction
                                receipt.subscription = subscription
                                receipt.meta.update(payment.result)
                                receipt.meta['payment_amount'] = payment.amount
                                receipt.save()
                                
                                receipt.products.add(offer.products.first())
                            else:
                                # Only receipts for settled transactions should exists
                                receipt.deleted = True
                                receipt.save()

            except ObjectDoesNotExist as exce:
                logger.exception(f"sync_subscriptions exception: {exce}")
            except MultipleObjectsReturned as exce:
                logger.exception(f"sync_subscriptions exception: {exce}")
            except Exception as exce:
                logger.exception(f"sync_subscriptions exception: {exce}")
    
    logger.info(f"sync_subscriptions Finished Subscription Migration")

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
                            invoice=invoice
                            )
                payment.result = {}
                payment.result['payment_info'] = payment_info
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
