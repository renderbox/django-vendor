from vendor.config import VENDOR_PAYMENT_PROCESSOR
from django.utils.module_loading import import_string

def get_payment_processor():
    PaymentProcessor = import_string('vendor.processors.{}'.format(VENDOR_PAYMENT_PROCESSOR))
    return PaymentProcessor