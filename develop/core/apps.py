from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        from core.signals import post_auth, pre_auth, process_auth, sub_cancel

        from vendor.processors.base import (
            vendor_post_authorization,
            vendor_pre_authorization,
            vendor_process_payment,
            vendor_subscription_cancel,
        )

        vendor_pre_authorization.connect(pre_auth)
        vendor_post_authorization.connect(post_auth)
        vendor_process_payment.connect(process_auth)
        vendor_subscription_cancel.connect(sub_cancel)
