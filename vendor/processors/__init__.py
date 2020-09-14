from vendor.config import VENDOR_PAYMENT_PROCESSOR
from django.utils.module_loading import import_string

PaymentProcessor = import_string('vendor.processors.{}'.format(VENDOR_PAYMENT_PROCESSOR))