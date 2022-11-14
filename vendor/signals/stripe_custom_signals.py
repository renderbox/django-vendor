from django.dispatch import Signal

# Signal for Stripe webhook
customer_source_expiring = Signal(providing_args=["site", "email"])
