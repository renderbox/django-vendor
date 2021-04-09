from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings

from vendor.models import Offer, Price, Invoice, OrderItem, Receipt, CustomerProfile, Payment
from vendor.forms import BillingAddressForm, CreditCardForm

User = get_user_model()

class ModelInvoiceTests(TestCase):

    fixtures = ['user', 'unit_test']

    def setUp(self):
        self.existing_invoice = Invoice.objects.get(pk=1)
        
        self.new_invoice = Invoice(profile=CustomerProfile.objects.get(pk=1))
        self.new_invoice.save()

        self.shirt_offer = Offer.objects.get(pk=1)
        self.hamster = Offer.objects.get(pk=3)
        self.mug_offer = Offer.objects.get(pk=4)
 
    def test_default_site_id_saved(self):
        invoice = Invoice()
        invoice.profile = CustomerProfile.objects.get(pk=1)
        invoice.save()

        self.assertEquals(Site.objects.get_current(), invoice.site)

    def test_add_offer(self):
        self.existing_invoice.add_offer(Offer.objects.get(pk=4))
        self.new_invoice.add_offer(self.mug_offer)

        self.assertIsNotNone(OrderItem.objects.get(invoice=self.new_invoice))
        self.assertEquals(OrderItem.objects.filter(invoice=self.existing_invoice).count(), 4)

    # def test_fail_add_unavailable_offer(self):
        # raise NotImplementedError()

    def test_remove_offer(self):
        self.existing_invoice.remove_offer(Offer.objects.get(pk=3))

        self.assertEquals(OrderItem.objects.filter(invoice=self.existing_invoice).count(), 2)

    def test_update_totals(self):
        self.existing_invoice.update_totals()
        start_total = self.existing_invoice.total

        self.existing_invoice.add_offer(Offer.objects.get(pk=4))
        self.existing_invoice.update_totals()
        add_mug_total = self.existing_invoice.total

        self.existing_invoice.remove_offer(Offer.objects.get(pk=1))
        self.existing_invoice.update_totals()
        remove_shirt_total = self.existing_invoice.total

        self.assertEquals(start_total, 345.18)
        self.assertEquals(add_mug_total, 355.18)
        self.assertEquals(remove_shirt_total, 345.19)

    def test_add_quantity(self):
        self.shirt_offer.allow_multiple = True
        self.shirt_offer.save()
        start_quantity = self.existing_invoice.order_items.filter(offer=self.shirt_offer).first().quantity
        self.existing_invoice.add_offer(self.shirt_offer)
        end_quantity = self.existing_invoice.order_items.filter(offer=self.shirt_offer).first().quantity
        
        self.assertNotEquals(start_quantity, end_quantity)

    def test_remove_quantity(self):
        start_quantity = self.existing_invoice.order_items.filter(offer=self.shirt_offer).first().quantity
        self.existing_invoice.remove_offer(self.shirt_offer)
        end_quantity = self.existing_invoice.order_items.filter(offer=self.shirt_offer).first().quantity

        self.assertNotEquals(start_quantity, end_quantity)

    def test_remove_quantity_zero(self):
        start_quantity = self.existing_invoice.order_items.filter(offer=self.hamster).first().quantity
        self.existing_invoice.remove_offer(self.hamster)
        end_quantity = self.existing_invoice.order_items.filter(offer=self.hamster).count()

        self.assertNotEquals(start_quantity, end_quantity)

    def test_get_recurring_total(self):
        recurring_offer = Offer.objects.get(pk=5)
        self.existing_invoice.add_offer(recurring_offer)
        
        self.assertEquals(self.existing_invoice.get_recurring_total(), recurring_offer.current_price())

    def test_get_recurring_total_only_recurring_order_items(self):
        recurring_offer = Offer.objects.get(pk=5)
        self.new_invoice.add_offer(recurring_offer)
        
        self.assertEquals(self.new_invoice.get_recurring_total(), recurring_offer.current_price())
        self.assertEquals(self.new_invoice.get_one_time_transaction_total(), 0)

    def test_get_one_time_transaction_total_with_recurring_offer(self):
        recurring_offer = Offer.objects.get(pk=5)
        self.existing_invoice.add_offer(recurring_offer)
        
        self.assertEquals(self.existing_invoice.get_one_time_transaction_total(), self.existing_invoice.total - self.existing_invoice.get_recurring_total())

    def test_get_one_time_transaction_total_no_recurring_order_items(self):
        recurring_offer = Offer.objects.get(pk=5)
        self.existing_invoice.add_offer(recurring_offer)
        
        self.assertEquals(self.existing_invoice.get_one_time_transaction_total(), self.existing_invoice.total - self.existing_invoice.get_recurring_total())
        self.assertEquals(self.existing_invoice.get_recurring_total(), 0)

    def test_get_recurring_order_items(self):
        recurring_offer = Offer.objects.get(pk=5)
        self.existing_invoice.add_offer(recurring_offer)

        self.assertEquals(self.existing_invoice.get_recurring_order_items().count(), 1)
    
    def test_get_one_time_transaction_order_items(self):
        recurring_offer = Offer.objects.get(pk=5)
        self.existing_invoice.add_offer(recurring_offer)

        self.assertEquals(self.existing_invoice.get_one_time_transaction_order_items().count(), self.existing_invoice.order_items.all().count() - 1)

    def test_empty_cart(self):
        self.assertNotEqual(0, self.existing_invoice.order_items.count())
        self.existing_invoice.empty_cart()
        self.assertEqual(0, self.existing_invoice.order_items.count())

    def test_empty_cart_in_checkout_state(self):
        self.existing_invoice.status = Invoice.InvoiceStatus.CHECKOUT
        self.existing_invoice.save()
        self.assertNotEqual(0, self.existing_invoice.order_items.count())
        self.existing_invoice.empty_cart()
        self.assertEqual(0, self.existing_invoice.order_items.count())
    

class CartViewTests(TestCase):

    fixtures = ['user', 'unit_test']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)

        self.invoice = Invoice.objects.get(pk=1)
        
        self.mug_offer = Offer.objects.get(pk=4)
        self.shirt_offer = Offer.objects.get(pk=1)

        self.cart_url = reverse('vendor:cart')

    def test_view_cart_status_code(self):
        response = self.client.get(self.cart_url)
        self.assertEquals(response.status_code, 200)

    def test_view_cart_content_loads(self):
        response = self.client.get(self.cart_url)

        self.assertContains(response, f'<span>${self.invoice.subtotal:.2f}</span>')
        self.assertContains(response, f'<span>${self.invoice.tax:.2f}</span>')
        self.assertContains(response, f'<span>${self.invoice.shipping:.2f}</span>')
        self.assertContains(response, f'<span class="text-primary">${self.invoice.total:.2f}</span>')
        self.assertContains(response, f'<span class="font-weight-bolder">Total ({self.invoice.get_currency_display()}) </span>')

    def test_view_cart_empty(self):
        self.invoice.order_items.all().delete()
        response = self.client.get(self.cart_url)

        self.assertContains(response, 'Your shopping cart is empty.')
        self.assertNotContains(response, 'Check Out')
    
    def test_view_cart_updates_on_adding_items(self):
        response = self.client.get(self.cart_url)
        self.assertContains(response, f'<span class="text-primary">${self.invoice.total}</span>')

        add_mug_url = reverse("vendor:add-to-cart", kwargs={'slug': self.mug_offer.slug})
        self.client.post(add_mug_url)
        self.assertContains(response, f'<span class="text-primary">${self.invoice.total}</span>')

        remove_shirt_url = reverse("vendor:remove-from-cart", kwargs={'slug': self.shirt_offer.slug})
        self.assertContains(response, f'<span class="text-primary">${self.invoice.total}</span>')
    
    # def test_view_displays_login_instead_checkout(self):
        # raise NotImplementedError()
    
    
class AccountInformationViewTests(TestCase):

    fixtures = ['user', 'unit_test']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.view_url = reverse('vendor:checkout-account')
        self.invoice = Invoice.objects.get(pk=1)

    def test_view_status_code_200(self):
        response = self.client.get(self.view_url)
        self.assertEquals(response.status_code, 200)

    def test_view_redirect_login(self):
        self.client.logout()
        response = self.client.get(self.view_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_login')+ '?next=' + self.view_url )

    # def test_view_cart_no_shipping_address(self):
        # raise NotImplementedError()

    # def test_view_cart_status_code_redirect_add_offer(self):
        # raise NotImplementedError()

    # def test_view_cart_status_code_redirect_remove_offer(self):
        # raise NotImplementedError()

    # def test_cart_updates_to_zero_items(self):
        # raise NotImplementedError()


class PaymentViewTests(TestCase):

    fixtures = ['user', 'unit_test']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.view_url = reverse('vendor:checkout-payment')
        self.invoice = Invoice.objects.get(pk=1)

    def test_view_status_code_200(self):
        response = self.client.get(self.view_url)
        self.assertEquals(response.status_code, 200)

    def test_view_redirect_login(self):
        self.client.logout()
        response = self.client.get(self.view_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_login')+ '?next=' + self.view_url )
    
    # def test_view_cart_no_shipping_address(self):
        # raise NotImplementedError()

    # def test_view_cart_status_code_redirect_add_offer(self):
        # raise NotImplementedError()

    # def test_view_cart_status_code_redirect_remove_offer(self):
        # raise NotImplementedError()

    # def test_cart_updates_to_zero_items(self):
        # raise NotImplementedError()


class ReviewCheckoutViewTests(TestCase):

    fixtures = ['user', 'unit_test']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.view_url = reverse('vendor:checkout-review')
        self.invoice = Invoice.objects.get(pk=1)

    def test_view_status_code_200(self):
        response = self.client.get(self.view_url)
        self.assertEquals(response.status_code, 200)
        
    # def test_view_cart_no_shipping_address(self):
    #     raise NotImplementedError()
    
    def test_view_redirect_login(self):
        self.client.logout()
        response = self.client.get(self.view_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_login')+ '?next=' + self.view_url )

    def test_view_missing_data(self):
        session = self.client.session
        session['billing_address_form'] = BillingAddressForm().initial
        session['credit_card_form'] = CreditCardForm().initial
        session.save()
        self.invoice.status = Invoice.InvoiceStatus.CHECKOUT
        self.invoice.save()

        response = self.client.post(self.view_url)

        self.assertRedirects(response, reverse('vendor:checkout-account'))

    def test_view_payment_success(self):
        self.invoice.status = Invoice.InvoiceStatus.CHECKOUT
        self.invoice.save()
        Payment.objects.all().delete()
        form_data = {
            'billing_address_form': {
                'name': 'Home',
                'company': 'Whitemoon Dreams',
                'country': 840,
                'address_1': '221B Baker Street',
                'address_2': '',
                'locality': 'Marylebone',
                'state': 'California',
                'postal_code': '90292'},
            'credit_card_form': {
                'full_name': 'Bob Ross',
                'card_number': '5424000000000015',
                'expire_month': '12',
                'expire_year': '2030',
                'cvv_number': '900',
                'payment_type': '10'}
            }

        billing_address = BillingAddressForm(form_data['billing_address_form'])
        billing_address.is_bound = True
        billing_address.is_valid()
        payment_info = CreditCardForm(form_data['credit_card_form'])
        payment_info.is_bound = True
        payment_info.is_valid()

        session = self.client.session
        session['billing_address_form'] = billing_address.cleaned_data
        session['credit_card_form'] = payment_info.cleaned_data
        session.save()

        response = self.client.post(self.view_url)

        self.assertEquals(self.invoice.payments.all().count(), 1)
    
    # def test_view_cart_no_shipping_address(self):
        # raise NotImplementedError()

    # def test_view_cart_status_code_redirect_add_offer(self):
        # raise NotImplementedError()

    # def test_view_cart_status_code_redirect_remove_offer(self):
        # raise NotImplementedError()

    # def test_cart_updates_to_zero_items(self):
        # raise NotImplementedError()
    

class PaymentSummaryViewTests(TestCase):

    fixtures = ['user', 'unit_test']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(pk=1)
        self.client.force_login(self.user)
        self.invoice = Invoice.objects.get(pk=1)
        self.view_url = reverse('vendor:purchase-summary', kwargs={'uuid': self.invoice.uuid})

    def test_view_status_code_200(self):
        response = self.client.get(self.view_url)
        self.assertEquals(response.status_code, 200)

    def test_view_redirect_login(self):
        self.client.logout()
        response = self.client.get(self.view_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_login')+ '?next=' + self.view_url )