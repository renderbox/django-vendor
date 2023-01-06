from django.contrib.sites.models import Site
from django.views.generic.list import ListView
from django.urls import reverse
from vendor.config import PaymentProcessorSiteConfig, PaymentProcessorSiteSelectSiteConfig,\
    PaymentProcessorForm, PaymentProcessorSiteSelectForm
from siteconfigs.models import SiteConfigModel
from vendor.views.mixin import SiteOnRequestFilterMixin, get_site_from_request
from django.views.generic.edit import FormView
from django.shortcuts import redirect

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
