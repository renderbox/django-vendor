from django.dispatch import receiver
from vendor.processors.base import vendor_post_authorization, vendor_process_payment, \
    vendor_pre_authorization, vendor_subscription_cancel

# Example Signals use
@receiver(vendor_pre_authorization)
def pre_auth(sender, invoice, **kwargs):
    # print("pre auth")
    pass

@receiver(vendor_process_payment)
def process_auth(sender, invoice, **kwargs):
    # print("process payment")
    pass

@receiver(vendor_post_authorization)
def post_auth(sender, invoice, **kwargs):
    # print("post auth")
    pass

@receiver(vendor_subscription_cancel)
def sub_cancel(sender, **kwargs):
    # print("post auth")
    pass

