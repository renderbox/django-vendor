from django.conf import settings
from django.utils.module_loading import import_string

PaymentProcessor = import_string('vendor.processors.{}'.format(settings.VENDOR_PAYMENT_PROCESSOR))