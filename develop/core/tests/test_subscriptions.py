from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from core.models import Product

from vendor.models import CustomerProfile, Subscription
from vendor.models.choice import SubscriptionStatus


class ModelSubscriptionTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.user = User(username='test', first_name='Bob', last_name='Ross', password='helloworld')
        self.user.save()
        self.customer_profile = CustomerProfile()
        self.customer_profile.user = User.objects.get(pk=2)
        self.customer_profile.save()

        self.customer_profile_existing = CustomerProfile.objects.get(pk=1)

        self.customer_profile_user = CustomerProfile()
        self.customer_profile_user.user = User.objects.get(pk=1)
        self.customer_profile_user.save()

    def test_void(self):
        # TODO: Finish this test
        pass

    def test_next_billing_date(self):
        # TODO: Finish this test
        pass

    def test_get_next_billing_date(self):
        # TODO: Finish this test
        pass