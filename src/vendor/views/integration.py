from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView
from vendor.integrations import AuthorizeNetIntegration, StripeIntegration

from vendor.forms import AuthorizeNetIntegrationForm, StripeIntegrationForm
from django.urls import reverse_lazy
from vendor.views.mixin import get_site_from_request


class AuthorizeNetIntegrationView(LoginRequiredMixin, FormView):
    template_name = "vendor/integration_form.html"
    form_class = AuthorizeNetIntegrationForm
    success_url = reverse_lazy('vendor_admin:authorizenet-integration')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        authorizenet_integration = AuthorizeNetIntegration(get_site_from_request(self.request))
        context['integration_name'] = _("AuthorizeNet Integration")

        context['form'] = AuthorizeNetIntegrationForm(instance=authorizenet_integration.instance)

        return context
    
    def form_valid(self, form):
        authorizenet_integration = AuthorizeNetIntegration(get_site_from_request(self.request))
        authorizenet_integration.save(form.cleaned_data)

        return super().form_valid(form)


class StripeIntegrationView(LoginRequiredMixin, FormView):
    template_name = "vendor/integration_form.html"
    form_class = StripeIntegrationForm
    success_url = reverse_lazy('vendor_admin:stripe-integration')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        stripe_integration = StripeIntegration(get_site_from_request(self.request))
        context['integration_name'] = _("Stripe Integration")

        context['form'] = StripeIntegrationForm(instance=stripe_integration.instance)

        return context
    
    def form_valid(self, form):
        stripe_integration = StripeIntegration(get_site_from_request(self.request))
        stripe_integration.save(form.cleaned_data)

        return super().form_valid(form)

