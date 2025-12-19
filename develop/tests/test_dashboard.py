from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class DashboardViewTests(TestCase):

    fixtures = ["user", "unit_test"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

    def test_view_payment_status_code(self):
        response = self.client.get(reverse("vendor_admin:manager-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Purchase Dashboard")

    def test_view_dashboard_status_code_fail_no_login(self):
        client = Client()
        response = client.get(reverse("vendor_admin:manager-dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
