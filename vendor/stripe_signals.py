from django.dispatch import Signal
# This signal file is needed to avoid django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet in signals.py

customer_source_expiring = Signal(providing_args=["site", "email"])
