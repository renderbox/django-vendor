from django.core.exceptions import ObjectDoesNotExist
from integrations.models import Credential
from vendor.forms import AuthorizeNetIntegrationForm, StripeIntegrationForm


class BaseIntegration(object):
    NAME = None

    site = None
    form_class = None

    def __init__(self, site):
        if not self.NAME:
            raise Exception('NAME is required for all BaseIntegration instances')

        self.site = site
        self.instance = self.get_instance()

    def get_instance(self):
        try:
            return Credential.objects.get(name=self.NAME, site=self.site)
        except ObjectDoesNotExist:
            return None

    def save(self, data):
        if not self.instance:
            form = self.form_class(data)
        else:
            form = self.form_class(data, instance=self.instance)

        integration_form = form.save(commit=False)
        integration_form.name = self.NAME
        integration_form.site = self.site
        integration_form.save()


class AuthorizeNetIntegration(BaseIntegration):
    NAME = "AuthorizeNet Integration"

    site = None
    form_class = AuthorizeNetIntegrationForm


class StripeIntegration(BaseIntegration):
    NAME = "Stripe Integration"

    site = None
    form_class = StripeIntegrationForm
