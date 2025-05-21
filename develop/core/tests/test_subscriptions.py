from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from vendor.models import CustomerProfile, Subscription
from vendor.models.choice import PurchaseStatus, SubscriptionStatus


class ModelSubscriptionTests(TestCase):

    fixtures = ["user", "unit_test"]

    def setUp(self):
        self.user = User(
            username="test", first_name="Bob", last_name="Ross", password="helloworld"
        )
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

    def test_get_reports_manager(self):
        # TODO: Finish this test
        pass


class SubscriptionViewTests(TestCase):

    fixtures = ["user", "unit_test"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

        self.profile = CustomerProfile.objects.get(pk=1)
        self.subscription = Subscription.objects.get(pk=1)

        self.subscription_list_uri = reverse("vendor_admin:manager-subscriptions")
        self.subscription_detail_uri = reverse(
            "vendor_admin:manager-subscription", kwargs={"uuid": self.subscription.uuid}
        )
        self.subscription_create_uri = reverse(
            "vendor_admin:manager-subscription-create"
        )
        self.subscription_add_payment_uri = reverse(
            "vendor_admin:manager-subscription-add-payment",
            kwargs={
                "uuid_subscription": self.subscription.uuid,
                "uuid_profile": self.profile.uuid,
            },
        )

    def test_admin_subscription_list_success(self):
        response = self.client.get(self.subscription_list_uri)

        self.assertEquals(response.status_code, 200)

    def test_admin_subscription_detail_success(self):
        response = self.client.get(self.subscription_detail_uri)

        self.assertEquals(response.status_code, 200)

    def test_admin_subscription_detail_fail(self):
        non_exiting_subscriptin_uri = reverse(
            "vendor_admin:manager-subscription", kwargs={"uuid": self.profile.uuid}
        )
        response = self.client.get(non_exiting_subscriptin_uri)

        self.assertEquals(response.status_code, 404)

    def test_admin_subscription_create_success(self):
        response = self.client.get(self.subscription_create_uri)

        self.assertEquals(response.status_code, 200)
        self.assertNotContains(response, "gateway_id")

    def test_admin_subscription_create_apply_site_filter_success(self):
        response = self.client.get(f"{self.subscription_create_uri}?site=1")

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "subscription_id")

    def test_admin_subscription_create_post_success(self):
        post_data = {
            "site": 1,
            "subscription_id": "3214",
            "status": SubscriptionStatus.ACTIVE,
            "profile": 1,
        }

        response = self.client.post(self.subscription_create_uri, data=post_data)

        self.assertEquals(response.status_code, 302)

    def test_admin_subscription_add_payment_success(self):
        response = self.client.get(self.subscription_add_payment_uri)

        self.assertEquals(response.status_code, 200)

    def test_admin_subscription_add_payment_apply_site_filter_success(self):
        response = self.client.get(f"{self.subscription_add_payment_uri}?site=1")

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "transaction")

    def test_admin_subscription_add_payment_post_success(self):
        post_data = {
            "subscription": 1,
            "offer": 1,
            "profile": 1,
            "transaction": "3214",
            "amount": 13.33,
            "submitted_date": timezone.now(),
            "success": True,
            "status": PurchaseStatus.SETTLED,
            "payee_full_name": "Bob Ross",
        }

        response = self.client.post(
            f"{self.subscription_add_payment_uri}?site=1", data=post_data
        )

        self.assertEquals(response.status_code, 302)
