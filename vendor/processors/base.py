"""
Base Payment processor used by all derived processors.
"""
import django.dispatch

from decimal import Decimal, ROUND_DOWN
from django.conf import settings
from django.utils import timezone

from vendor import config
from vendor.forms import CreditCardForm, BillingAddressForm
from vendor.models import Payment, Invoice, Receipt, Subscription
from vendor.models.choice import PurchaseStatus, SubscriptionStatus, TermType, InvoiceStatus, PaymentTypes
from vendor.utils import get_payment_scheduled_end_date, get_subscription_start_date, get_future_date_days

##########
# SIGNALS
vendor_pre_authorization = django.dispatch.Signal()
vendor_process_payment = django.dispatch.Signal()
vendor_post_authorization = django.dispatch.Signal()
vendor_subscription_cancel = django.dispatch.Signal()
vendor_customer_card_expiring = django.dispatch.Signal()


#############
# BASE CLASS
class PaymentProcessorBase(object):
    """
    Setup the core functionality for all processors.
    """
    API_ENDPOINT = None

    status = None
    invoice = None
    provider = None
    # TODO: Change payment to a list as an invoice can have multiple payment. EG: 1 for 1 type purchases and n for any amount of subscriptions. 
    payment = None
    subscription = None
    subscription_id = None
    receipt = None
    payment_info = {}
    billing_address = {}
    transaction_token = None
    transaction_id = ""
    transaction_succeeded = False
    transaction_info = {}
    transaction_response = None

    def __init__(self, site, invoice=None):
        """
        This should not be overriden.  Override one of the methods it calls if you need to.
        """
        if invoice:
            self.set_invoice(invoice)

        self.provider = self.__class__.__name__
        self.processor_setup(site)
        self.set_api_endpoint()

    def set_api_endpoint(self):
        """
        Sets the API endpoint for debugging or production.It is dependent on the VENDOR_STATE
        enviornment variable. Default value is DEBUG for the VENDOR_STATE this function
        should be overwrote upon necesity of each Payment Processor
        """
        if config.VENDOR_STATE == 'DEBUG':
            self.API_ENDPOINT = None
        elif config.VENDOR_STATE == 'PRODUCTION':
            self.API_ENDPOINT = None

    def processor_setup(self, site):
        """
        This is for setting up any of the settings needed for the payment processing.
        For example, here you would set the
        """
        pass

    def set_payment_info(self, **kwargs):
        self.payment_info = kwargs

    def set_invoice(self, invoice):
        self.invoice = invoice

    def create_payment_model(self, amount=None):
        """
        Create payment instance with base information to track payment submissions
        """
        if not amount:
            amount = self.invoice.total

        self.payment = Payment(profile=self.invoice.profile,
                               amount=amount,
                               provider=self.provider,
                               invoice=self.invoice,
                               created=timezone.now()
                               )

        if not self.payment.result:
            self.payment.result = {}
        
        self.payment.result['payment_info'] = {
            'account_number': self.payment_info.cleaned_data.get('card_number')[-4:],
            'full_name': self.payment_info.cleaned_data.get('full_name')
        }
        self.payment.payee_full_name = self.payment_info.cleaned_data.get('full_name')
        self.payment.payee_company = self.billing_address.cleaned_data.get('company')
        self.payment.status = PurchaseStatus.QUEUED
        self.payment.submitted_date = timezone.now()

        billing_address = self.billing_address.save(commit=False)
        billing_address, created = self.invoice.profile.get_or_create_address(billing_address)

        if created:
            billing_address.profile = self.invoice.profile
            billing_address.save()

        self.payment.billing_address = billing_address
        self.payment.save()

    def save_payment_transaction_result(self):
        """
        Saves the result output of any transaction.
        """
        self.payment.success = self.transaction_succeeded
        self.payment.transaction = self.transaction_id
        self.payment.result.update(self.transaction_info)
        self.payment.save()

    def get_payment_info(self, account_number=None, full_name=None):
        """
        Each processor should implement their own method, but they should
        all return at least the account_number and full_name as a dictionary.
        eg:
        """
        return {
            'account_number': account_number,
            'full_name': full_name
        }

    def get_transaction_info(self, raw='', errors='', payment_method='', data=''):
        return {
            'raw': raw,
            'errors': errors,
            'payment_method': payment_method,
            'data': data
        }

    def parse_response(self):
        ...

    def parse_success(self):
        ...

    def save_subscription_transaction_result(self):
        """
        Saves the result output of any transaction.
        """
        if self.transaction_succeeded:
            self.subscription.status = SubscriptionStatus.ACTIVE
            self.subscription.gateway_id = self.transaction
            
        self.subscription.meta[timezone.now().strftime("%Y-%m-%d_%H:%M:%S")] = self.transaction_info
        self.subscription.save()

    def update_invoice_status(self, new_status):
        """
        Updates the Invoice status if the transaction was submitted.
        Otherwise it returns the invoice to the Cart. The error is saved in
        the payment for the transaction.
        """
        if self.transaction_succeeded:
            self.invoice.status = new_status
        else:
            self.invoice.status = InvoiceStatus.CART

        self.invoice.save()

    def is_transaction_and_invoice_complete(self):
        """
        If payment was successful and invoice status is complete returns True. Otherwise
        false and no receipts should be created.
        """
        if self.transaction_succeeded and self.invoice.status == InvoiceStatus.COMPLETE:
            return True

        return False

    def create_receipt_by_term_type(self, order_item, term_type):
        today = timezone.now()
        self.receipt = Receipt()
        self.receipt.profile = self.invoice.profile
        self.receipt.order_item = order_item
        self.receipt.transaction = self.payment.transaction
        self.receipt.meta.update(self.payment.result)
        self.receipt.meta['payment_amount'] = self.payment.amount
        start_date = order_item.offer.get_term_start_date(today)
        self.receipt.start_date = get_subscription_start_date(order_item.offer, self.invoice.profile, start_date)
        self.receipt.save()

        if term_type < TermType.PERPETUAL:
            self.receipt.end_date = get_payment_scheduled_end_date(order_item.offer, self.receipt.start_date)
            self.receipt.subscription = self.subscription
            
        self.receipt.save()

    def create_trial_receipt_payment(self, order_item):
        if self.invoice.profile.has_owned_product(order_item.offer.products.all()):
            return None  # Trial receipts are only created if the user has not owned the product previously 

        if not order_item.offer.get_trial_days():
            return None

        start_date = order_item.offer.get_term_start_date()

        self.payment = Payment.objects.create(
            profile=self.invoice.profile,
            amount=0,
            provider=self.provider,
            invoice=self.invoice,
            submitted_date=start_date,
            success=True,
            status=PurchaseStatus.SETTLED,
            payee_full_name=" ".join([self.invoice.profile.user.first_name, self.invoice.profile.user.last_name])
        )
        
        self.payment.transaction = f"{self.payment.uuid}-trial"
        self.payment.save()

        self.receipt = Receipt.objects.create(
            profile=self.invoice.profile,
            order_item=order_item,
            transaction=self.payment.transaction,
            start_date=start_date,
            end_date=get_future_date_days(start_date, order_item.offer.get_trial_days()),
            subscription=self.subscription
        )

        if order_item.offer.terms < TermType.PERPETUAL:
            self.payment.subscription = self.subscription
            self.payment.save()
            
            self.receipt.subscription = self.subscription
            self.receipt.save()
            
    def create_order_item_receipt(self, order_item):
        """
        Creates a receipt for every product in the order item according to its,
        offering term type.
        """
        for product in order_item.offer.products.all():
            self.create_receipt_by_term_type(order_item, order_item.offer.terms)
            self.create_trial_receipt_payment(order_item)
            self.receipt.products.add(product)

    def create_receipts(self, order_items):
        """
        It then creates receipt for the order items supplied.
        """
        for order_item in order_items.all():
            self.create_order_item_receipt(order_item)

    def update_subscription_receipt(self, subscription, subscription_id, status):
        """
        subscription: OrderItem
        subscription_id: int
        status: PurchaseStatus
        """
        subscription_receipt = self.invoice.order_items.get(offer=subscription.offer).receipts.get(transaction=self.payment.transaction)
        subscription_receipt.meta['subscription_id'] = subscription_id
        subscription_receipt.status = status
        subscription_receipt.save()

    def amount(self):   # Retrieves the total amount from the invoice
        self.invoice.update_totals()
        return self.invoice.total

    def amount_without_subscriptions(self):
        subscription_total = sum([ oi.total for oi in self.invoice.order_items.filter(offer__terms=TermType.SUBSCRIPTION)])

        amount = self.invoice.total - subscription_total
        return amount

    def get_transaction_id(self):
        return f"{self.invoice.site.pk}-{self.invoice.pk}"

    def set_billing_address_form_data(self, form_data, form_class):
        self.billing_address = form_class(form_data)

    def set_payment_info_form_data(self, form_data, form_class):
        self.payment_info = form_class(form_data)

    def is_data_valid(self):
        if not (self.billing_address.is_valid() and self.payment_info.is_valid() and self.invoice and self.invoice.order_items.count()):
            return False
        return True

    # -------------------
    # Data for the View
    def get_checkout_context(self, request=None, context={}):
        '''
        The Invoice plus any additional values to include in the payment record.
        '''
        # context = deepcopy(context)
        context['invoice'] = self.invoice
        
        if 'credit_card_form' not in context:
            context['credit_card_form'] = CreditCardForm(initial={'payment_type': PaymentTypes.CREDIT_CARD})

        if 'billing_address_form' not in context:
            context['billing_address_form'] = BillingAddressForm()

        return context

    def get_header_javascript(self):
        """
        Scripts that are expected to show in the top of the template.

        This will return a list of relative static URLs to the scripts.
        """
        return []

    def get_javascript(self):
        """
        Scripts added to the bottom of the page in the normal js location.

        This will return a list of relative static URLs to the scripts.
        """
        return []

    def get_template(self):
        """
        Unique partial template for the processor
        """
        pass

    def to_valid_decimal(self, number):
        # TODO: Need to check currency to determin decimal places.
        return Decimal(number).quantize(Decimal('.00'))

    def to_stripe_valid_unit(self, number):
        if number > 0:
            return int(number) * 100
        return 0

    # -------------------
    # Process a Payment
    def authorize_payment(self):
        """
        This runs the chain of events in a transaction.
        This should not be overriden.  Override one of the methods it calls if you need to.
        """
        self.invoice.ordered_date = timezone.now()
        self.invoice.save()
        if not self.invoice.calculate_subtotal():
            self.free_payment()
            return None

        if not self.is_data_valid():
            return None

        self.status = PurchaseStatus.QUEUED     # TODO: Set the status on the invoice.  Processor status should be the invoice's status.
        vendor_pre_authorization.send(sender=self.__class__, invoice=self.invoice)

        self.pre_authorization()

        self.status = PurchaseStatus.ACTIVE     # TODO: Set the status on the invoice.  Processor status should be the invoice's status.
        vendor_process_payment.send(sender=self.__class__, invoice=self.invoice)

        if self.invoice.get_one_time_transaction_order_items():
            self.create_payment_model()
            self.process_payment()
            self.save_payment_transaction_result()
            self.update_invoice_status(InvoiceStatus.COMPLETE)
            if self.is_transaction_and_invoice_complete():
                self.invoice.save_discounts_vendor_notes()
                self.create_receipts(self.invoice.get_one_time_transaction_order_items())

        if self.invoice.get_recurring_order_items():
            self.process_subscriptions()

        vendor_post_authorization.send(sender=self.__class__, invoice=self.invoice)
        self.post_authorization()


        #TODO: Set the status based on the result from the process_payment()

    def pre_authorization(self):
        """
        Called before the authorization begins.
        """
        pass

    def process_payment(self):
        """
        Called to handle the authorization.
        This is where the core of the payment processing happens.
        """
        # Gateway Transaction goes here...
        pass

    def free_payment(self):
        """
        Called to handle an invoice with total zero.
        This are the base internal steps to process a free payment.
        """
        self.payment = Payment(profile=self.invoice.profile,
                               amount=self.invoice.total,
                               provider=self.provider,
                               invoice=self.invoice,
                               created=timezone.now()
                               )
        self.payment.save()
        self.transaction_succeeded = True
        self.payment.success = True
        self.payment.status = PurchaseStatus.SETTLED
        self.payment.transaction = f"{self.payment.uuid}-free"
        self.payment.payee_full_name = " ".join([self.invoice.profile.user.first_name, self.invoice.profile.user.last_name])
        self.payment.result.update({'first': True})
        self.payment.save()

        self.update_invoice_status(InvoiceStatus.COMPLETE)

        self.create_receipts(self.invoice.order_items.all())

    def post_authorization(self):
        """
        Called after the authorization is complete.
        """
        pass

    def capture_payment(self):
        """
        Called to handle the capture.  (some gateways handle this at the same time as authorize_payment() )
        """
        pass

    def void_payment(self):
        """
        Call to handle a payment that has not been settled and wants to be voided
        """
        self.payment.status = PurchaseStatus.VOID
        self.payment.save()

    # -------------------
    # Process a Subscription
    def process_subscriptions(self):
        """
        Process/subscribies recurring payments throught the payement gateway and creates a payment model for each subscription.
        If a payment is completed it will create a receipt for the subscription
        """
        if not self.is_card_valid():
            return None

        for subscription in self.invoice.get_recurring_order_items():
            self.create_payment_model()
            self.subscription_payment(subscription)
            self.save_payment_transaction_result()
            self.update_invoice_status(InvoiceStatus.COMPLETE)
            
            if self.is_transaction_and_invoice_complete():
                self.create_subscription_model()
                self.invoice.save_discounts_vendor_notes()
                self.create_order_item_receipt(subscription)

    def subscription_payment(self, subscription):
        """
        Call handels the authrization and creation for a subscription.
        """
        # Gateway Transaction goes here...
        pass

    def create_subscription_model(self):
        self.subscription = Subscription.objects.create(
            gateway_id=self.subscription_id,
            profile=self.invoice.profile,
            auto_renew=True,
            status=SubscriptionStatus.ACTIVE
        )
        self.subscription.meta['response'] = self.transaction_info
        self.subscription.save()
        self.payment.subscription = self.subscription
        self.payment.save()

    def subscription_info(self):
        pass

    def subscription_update_payment(self):
        pass

    def subscription_cancel(self, subscription):
        settled_payments = subscription.payments.filter(status=PurchaseStatus.SETTLED).count()
        
        if not (settled_payments or subscription.is_on_trial()):
            raise Exception("Need to be on trial or have a settled payment")

        subscription.cancel()
        vendor_subscription_cancel.send(sender=self.__class__, subscription=subscription)

    def is_card_valid(self):
        """
        Function to validate a credit card by method of makeing a microtransaction and voiding it if authorized.
        """
        pass

    def renew_subscription(self, subscription, payment_transaction_id="", payment_status=PurchaseStatus.QUEUED, payment_success=True):
        """
        Function to renew already paid subscriptions form the payment gateway provider.
        """
        self.subscription = subscription
        submitted_date = timezone.now()

        self.payment = Payment.objects.create(
            profile=subscription.profile,
            invoice=self.invoice,
            transaction=payment_transaction_id,
            submitted_date=submitted_date,
            subscription=subscription,
            amount=self.invoice.total,
            success=payment_success,
            status=payment_status,
            payee_full_name = " ".join([self.invoice.profile.user.first_name, self.invoice.profile.user.last_name])
        )

        self.create_receipts(self.invoice.order_items.all())

    def subscription_update_price(self, subscription, new_price, user):
        """
        Call to handle when a new subscription price needs to be approved.
        """
        now = timezone.now().strftime("%Y-%m-%d_%H:%M:%S")

        subscription.meta['price_update'] = {
            now: f'Price update ({new_price}) accepted by user: {user.username} on {now}'
        }

        subscription.save()
    
    # -------------------
    # Refund a Payment
    def refund_payment(self):
        ...

    def subscription_payment_failed(self, subscription, transaction_id):
        self.payment = Payment.objects.create(
            subscription=subscription,
            profile=self.invoice.profile,
            amount=self.invoice.total,
            provider=self.provider,
            invoice=self.invoice,
            submitted_date=self.invoice.ordered_date,
            transaction=transaction_id,
            status = PurchaseStatus.DECLINED,
            payee_full_name=" ".join([self.invoice.profile.user.first_name, self.invoice.profile.user.last_name])
        )

    ##########
    # Signals
    ##########
    def customer_card_expired(self, site, email):
        vendor_customer_card_expiring.send(sender=self.__class__, site_pk=site.pk, email=email)
