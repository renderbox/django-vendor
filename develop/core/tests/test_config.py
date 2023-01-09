from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse
from vendor.config import StripeConnectAccountForm, StripeConnectAccountConfig
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
        url = reverse('vendor_admin:manager-config-stripe-connect-edit', kwargs={'pk': self.stripe_config.pk})
        
        response = self.client.post(url)
        self.assertEquals(response.status_code, 200)

    def test_stripe_config_edit_post_success(self):
        url = reverse('vendor_admin:manager-config-stripe-connect-edit', kwargs={'pk': self.stripe_config.pk})
        
        config_data = {
            'account_number': "123-test"
        }

        response = self.client.post(url, data=config_data)
        stripe_config = StripeConnectAccountConfig(Site.objects.get(pk=1))

        self.assertEquals(stripe_config.value.get('stripe_connect_account'), config_data['account_number'])
        self.assertEquals(response.status_code, 302)

