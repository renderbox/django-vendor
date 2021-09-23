from django.core.exceptions import ObjectDoesNotExist
from integrations.models import Credential
from vendor.forms import AuthorizeNetIntegrationForm


# TODO: Could implement an IntegrationBase Class in package.
class AuthorizeNetIntegration(object):
    NAME = "AuthorizeNet Integration"

    site = None
    form_class = AuthorizeNetIntegrationForm

    def __init__(self, site):
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
        
        authorizenet = form.save(commit=False)
        authorizenet.name = self.NAME
        authorizenet.site = self.site
        authorizenet.save()