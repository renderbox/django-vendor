from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from vendor.processors.base import vendor_post_authorization, vendor_process_payment, vendor_pre_authorization, vendor_subscription_cancel
        from core.signals import pre_auth, post_auth, process_auth, sub_cancel
        vendor_pre_authorization.connect(pre_auth)
        vendor_post_authorization.connect(post_auth)
        vendor_process_payment.connect(process_auth)
        vendor_subscription_cancel.connect(sub_cancel)