from django.dispatch import receiver
from vendor.processors.base import vendor_post_authorization, vendor_process_payment, vendor_pre_authorization


@receiver(vendor_pre_authorization)
def pre_auth(sender, invoice, **kwargs):
    print("pre auth")

@receiver(vendor_process_payment)
def process_auth(sender, invoice, **kwargs):
    print("process payment")

@receiver(vendor_post_authorization)
def post_auth(sender, invoice, **kwargs):
    print("post auth")
