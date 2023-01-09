from django.utils.translation import gettext_lazy as _
from django.contrib.sites.models import Site
from django.views.generic.list import ListView
from django.urls import reverse
from vendor.config import PaymentProcessorSiteConfig, PaymentProcessorSiteSelectSiteConfig,\
    PaymentProcessorForm, PaymentProcessorSiteSelectForm, StripeConnectAccountConfig, StripeConnectAccountForm
from siteconfigs.models import SiteConfigModel
from vendor.views.mixin import SiteOnRequestFilterMixin, get_site_from_request
from django.views.generic.edit import FormView, UpdateView
from django.shortcuts import redirect
from django.shortcuts import render

class PaymentProcessorSiteConfigsListView(ListView):
    template_name = 'vendor/manage/processor_site_config_list.html'
    model = SiteConfigModel

    def get_queryset(self):
        payment_processor = PaymentProcessorSiteConfig()

        return SiteConfigModel.objects.filter(key=payment_processor.key)


class PaymentProcessorSiteFormView(SiteOnRequestFilterMixin, FormView):
    template_name = 'vendor/manage/processor_site_config.html'
    form_class = PaymentProcessorForm

    def get_success_url(self):
        return reverse('vendor_admin:vendor-site-processor')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        site = get_site_from_request(self.request)
        processor_config = PaymentProcessorSiteConfig(site)
        context['form'] = processor_config.get_form()

        return context

    def form_valid(self, form):
        site = get_site_from_request(self.request)
        processor_config = PaymentProcessorSiteConfig(site)
        processor_config.save(form.cleaned_data["payment_processor"], "payment_processor")

        return redirect('vendor_admin:vendor-processor-lists')


class PaymentProcessorSiteSelectFormView(FormView):
    template_name = 'vendor/manage/processor_site_config.html'
    form_class = PaymentProcessorSiteSelectForm

    def get_success_url(self):
        return reverse('vendor_admin:processor-lists')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        
        if self.kwargs.get('domain'):
            site = Site.objects.get(domain=self.kwargs.get('domain'))
            processor_config = PaymentProcessorSiteSelectSiteConfig(site)
        else:
            processor_config = PaymentProcessorSiteSelectSiteConfig()
        context['form'] = processor_config.get_form()

        return context

    def form_valid(self, form):
        site = Site.objects.get(pk=form.cleaned_data['site'])
        processor_config = PaymentProcessorSiteSelectSiteConfig(site)
        processor_config.save(form.cleaned_data["payment_processor"], "payment_processor")
        
        return redirect('vendor_admin:vendor-processor-lists')


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



