
from django import template
from django.urls import reverse
from vendor.config import PaymentProcessorSiteConfig, StripeConnectAccountConfig
from siteconfigs.models import SiteConfigModel

register = template.Library()

@register.inclusion_tag('vendor/includes/edit_link.html')
def config_edit_link(config_key, config_pk):
    config = SiteConfigModel.objects.get(pk=config_pk)

    link = ''

    if config.key == PaymentProcessorSiteConfig().key:
        link = reverse('vendor_admin:manager-config-processor-update', kwargs={'pk': config_pk})
    elif config.key == StripeConnectAccountConfig().key:
        link = reverse('vendor_admin:manager-config-stripe-connect-update', kwargs={'pk': config_pk})


    return {
        'link': link
    }