from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse
from vendor.config import PaymentProcessorSiteConfig, StripeConnectAccountConfig, SupportedPaymentProcessor, VendorSiteCommissionConfig
from vendor.models import CustomerProfile
from siteconfigs.models import SiteConfigModel


class StripeConnectAccountConfigTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.customer_profile = CustomerProfile.objects.get(pk=1)
        self.stripe_config = SiteConfigModel.objects.get(pk=1) 

    def test_stripe_config_list_success(self):
        url = reverse('vendor_admin:manager-config-stripe-connect-list')

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_stripe_config_create_get_success(self):
        url = reverse('vendor_admin:manager-config-stripe-connect-create')

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_stripe_config_create_post_success(self):
        url = reverse('vendor_admin:manager-config-stripe-connect-create')

        site_two = Site.objects.get(pk=2)
        config_data = {
            'site': site_two.pk,
            'account_number': "321-test"
        }

        response = self.client.post(url, data=config_data)
        stripe_config_site_two = StripeConnectAccountConfig(site_two)
        
        self.assertEquals(stripe_config_site_two.value.get('stripe_connect_account'), config_data['account_number'])
        self.assertEquals(response.status_code, 302)

    def test_stripe_config_edit_get_success(self):
        url = reverse('vendor_admin:manager-config-stripe-connect-update', kwargs={'pk': self.stripe_config.pk})
        
        response = self.client.post(url)
        self.assertEquals(response.status_code, 200)

    def test_stripe_config_edit_post_success(self):
        url = reverse('vendor_admin:manager-config-stripe-connect-update', kwargs={'pk': self.stripe_config.pk})
        
        config_data = {
            'account_number': "123-test"
        }

        response = self.client.post(url, data=config_data)
        stripe_config = StripeConnectAccountConfig(Site.objects.get(pk=1))

        self.assertEquals(stripe_config.value.get('stripe_connect_account'), config_data['account_number'])
        self.assertEquals(response.status_code, 302)


class SiteProcessorConfigTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.customer_profile = CustomerProfile.objects.get(pk=1)
        self.processor_config = SiteConfigModel.objects.get(pk=2) 

    def test_processor_config_list_success(self):
        url = reverse('vendor_admin:manager-config-processor-list')

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_processor_config_create_get_success(self):
        url = reverse('vendor_admin:manager-config-processor-create')

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_processor_config_create_post_success(self):
        url = reverse('vendor_admin:manager-config-processor-create')

        site_two = Site.objects.get(pk=2)
        config_data = {
            'site': site_two.pk,
            'payment_processor': SupportedPaymentProcessor.AUTHORIZE_NET
        }

        response = self.client.post(url, data=config_data)
        payment_config = PaymentProcessorSiteConfig(site_two)
        
        self.assertEquals(payment_config.value.get('payment_processor'), config_data['payment_processor'])
        self.assertEquals(response.status_code, 302)

    def test_processor_config_edit_get_success(self):
        url = reverse('vendor_admin:manager-config-processor-update', kwargs={'pk': self.processor_config.pk})
        
        response = self.client.post(url)
        self.assertEquals(response.status_code, 200)

    def test_processor_config_edit_post_success(self):
        url = reverse('vendor_admin:manager-config-processor-update', kwargs={'pk': self.processor_config.pk})
        
        config_data = {
            'payment_processor': SupportedPaymentProcessor.STRIPE
        }

        response = self.client.post(url, data=config_data)
        payment_config = PaymentProcessorSiteConfig(Site.objects.get(pk=1))

        self.assertEquals(payment_config.value.get('payment_processor'), config_data['payment_processor'])
        self.assertEquals(response.status_code, 302)



class VendorSiteCommissionConfigTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.customer_profile = CustomerProfile.objects.get(pk=1)
        self.commission_config = SiteConfigModel.objects.get(pk=3)

    def test_vendor_site_commission_config_list_success(self):
        url = reverse('vendor_admin:manager-config-commission-list')

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_vendor_site_commission_config_create_get_success(self):
        url = reverse('vendor_admin:manager-config-commission-create')

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_vendor_site_commission_config_create_post_success(self):
        url = reverse('vendor_admin:manager-config-commission-create')

        site = Site.objects.get(pk=2)
        config_data = {
            'site': site.pk,
            'commission': 33
        }

        response = self.client.post(url, data=config_data)
        commission_config = VendorSiteCommissionConfig(site)
        
        self.assertEquals(commission_config.value.get('commission'), config_data['commission'])
        self.assertEquals(response.status_code, 302)

    def test_vendor_site_commission_config_edit_get_success(self):
        url = reverse('vendor_admin:manager-config-commission-update', kwargs={'pk': self.commission_config.pk})
        
        response = self.client.post(url)
        self.assertEquals(response.status_code, 200)

    def test_vendor_site_commission_config_edit_post_success(self):
        url = reverse('vendor_admin:manager-config-commission-update', kwargs={'pk': self.commission_config.pk})
        
        config_data = {
            'commission': 55
        }

        response = self.client.post(url, data=config_data)
        commission_config = VendorSiteCommissionConfig(Site.objects.get(pk=1))

        self.assertEquals(commission_config.value.get('commission'), config_data['commission'])
        self.assertEquals(response.status_code, 302)

