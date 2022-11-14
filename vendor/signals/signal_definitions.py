import django


##########
# SIGNALS
vendor_pre_authorization = django.dispatch.Signal()
vendor_process_payment = django.dispatch.Signal()
vendor_post_authorization = django.dispatch.Signal()
vendor_subscription_cancel = django.dispatch.Signal()
customer_source_expiring = django.dispatch.Signal()