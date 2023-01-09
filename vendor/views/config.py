from django.contrib.sites.models import Site
from django.views.generic.list import ListView
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView, UpdateView
from django.shortcuts import redirect, render

from vendor.views.mixin import SiteOnRequestFilterMixin, get_site_from_request
from vendor.config import PaymentProcessorSiteConfig, PaymentProcessorForm,\
    StripeConnectAccountConfig, StripeConnectAccountForm
from siteconfigs.models import SiteConfigModel


class PaymentProcessorSiteConfigsListView(ListView):
    template_name = 'vendor/manage/config_list.html'
    model = SiteConfigModel

    def get_queryset(self):
        payment_processor = PaymentProcessorSiteConfig()

        return SiteConfigModel.objects.filter(key=payment_processor.key)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        processot_config = PaymentProcessorSiteConfig()

        context['title'] = 'Payment Processors Configured'
        context['config_key'] = processot_config.key
        context['new_url'] = reverse('vendor_admin:manager-config-processor-create')

        return context


class PaymentProcessorCreateConfigView(FormView):
    template_name = 'vendor/manage/config.html'
    form_class = PaymentProcessorForm

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        processor_config = PaymentProcessorSiteConfig()
        form = self.get_form()

        existing_stripe_configs = SiteConfigModel.objects.filter(key=processor_config.key)
        sites = Site.objects.exclude(pk__in=[config.site.pk for config in existing_stripe_configs])
        form.fields['site'].queryset = sites

        context['title'] = _("Payment Processor Config")
        context['form'] = form
        context['cancel_url'] = reverse('vendor_admin:manager-config-processor-list')

        return context

    def form_valid(self, form):
        site = form.cleaned_data['site']

        processor_config = PaymentProcessorSiteConfig(site)
        processor_config.save(form.cleaned_data["payment_processor"], "payment_processor")
        
        return redirect('vendor_admin:manager-config-processor-list')


class PaymentProcessorUpdateConfigView(UpdateView):
    template_name = 'vendor/manage/config.html'
    model = SiteConfigModel
    form_class = PaymentProcessorForm

    def get_form(self, **kwargs):
        return PaymentProcessorForm()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_model = self.get_object()
        processor_config = PaymentProcessorSiteConfig(config_model.site)

        context['title'] = _("Edit Payment Processor Config")
        context['form'] = PaymentProcessorForm(initial={'site': config_model.site, 'payment_processor': processor_config.get_key_value('payment_processor')})
        context['form'].fields['site'].disabled = True
        context['cancel_url'] = reverse('vendor_admin:manager-config-processor-list')

        return context


    def post(self, request, *args, **kwargs):
        # Get the SiteConfigModel instance passed through the url
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)

        form = self.get_form_class()(request.POST)
        # Make this site field required False since you can only update the account_number
        form.fields['site'].required = False

        if not form.is_valid():
            context['form'] = form
            return render(request, self.template_name, context)
        
        processor_config = PaymentProcessorSiteConfig(self.object.site)
        processor_config.save(form.cleaned_data['payment_processor'], "payment_processor")

        return redirect("vendor_admin:manager-config-processor-list")


class StripeConnectAccountCreateConfigView(FormView):
    template_name = 'vendor/manage/config.html'
    form_class = StripeConnectAccountForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stripe_config = StripeConnectAccountConfig()
        form = self.get_form()

        existing_stripe_configs = SiteConfigModel.objects.filter(key=stripe_config.key)
        sites = Site.objects.exclude(pk__in=[config.site.pk for config in existing_stripe_configs])
        form.fields['site'].queryset = sites

        context['title'] = _("Stripe Connect Account")
        context['form'] = form
        context['cancel_url'] = reverse('vendor_admin:manager-config-stripe-connect-list')

        return context

    def form_valid(self, form):
        site = form.cleaned_data['site']
        
        stripe_connect = StripeConnectAccountConfig(site)
        stripe_connect.save(form.cleaned_data['account_number'], "stripe_connect_account")

        return redirect("vendor_admin:manager-config-stripe-connect-list")


class StripeConnectAccountCongifListView(ListView):
    template_name = 'vendor/manage/config_list.html'
    model = SiteConfigModel

    def get_queryset(self):
        stripe_config = StripeConnectAccountConfig()
        
        return self.model.objects.filter(key=stripe_config.key)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stripe_config = StripeConnectAccountConfig()

        context['title'] = 'Stripe Connect Accounts'
        context['config_key'] = stripe_config.key
        context['new_url'] = reverse('vendor_admin:manager-config-stripe-connect-create')

        return context


class StripeConnectAccountUpdateConfigView(UpdateView):
    template_name = 'vendor/manage/config.html'
    model = SiteConfigModel
    form_class = StripeConnectAccountForm

    def get_form(self, **kwargs):
        return StripeConnectAccountForm()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_model = self.get_object()
        stripe_config = StripeConnectAccountConfig(config_model.site)

        context['title'] = _("Stripe Connect Account")
        context['form'] = StripeConnectAccountForm(initial={'site': config_model.site, 'account_number': stripe_config.get_key_value('stripe_connect_account')})
        context['form'].fields['site'].disabled = True
        context['cancel_url'] = reverse('vendor_admin:manager-config-stripe-connect-list')

        return context


    def post(self, request, *args, **kwargs):
        # Get the SiteConfigModel instance passed through the url
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)

        form = self.get_form_class()(request.POST)
        # Make this site field required False since you can only update the account_number
        form.fields['site'].required = False

        if not form.is_valid():
            context['form'] = form
            return render(request, self.template_name, context)
        
        stripe_connect = StripeConnectAccountConfig(self.object.site)
        stripe_connect.save(form.cleaned_data['account_number'], "stripe_connect_account")

        return redirect("vendor_admin:manager-config-stripe-connect-list")



