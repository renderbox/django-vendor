from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase, Client
from django.urls import reverse

from vendor.models import Offer, Invoice, OrderItem, CustomerProfile, Payment, Price
from vendor.models.choice import InvoiceStatus
from vendor.forms import BillingAddressForm, CreditCardForm
from vendor.utils import get_display_decimal

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
        before_remove_count = self.existing_invoice.order_items.count()
        self.existing_invoice.remove_offer(Offer.objects.get(pk=3))

        self.assertEquals(self.existing_invoice.order_items.count(), before_remove_count - 1)

    def test_update_totals(self):
        self.existing_invoice.update_totals()
        start_total = self.existing_invoice.total

        self.existing_invoice.add_offer(Offer.objects.get(pk=2))
        self.existing_invoice.update_totals()
        add_mug_total = self.existing_invoice.total

        self.existing_invoice.remove_offer(Offer.objects.get(pk=2))
        self.existing_invoice.update_totals()
        remove_shirt_total = self.existing_invoice.total

        self.assertEquals(get_display_decimal(add_mug_total), get_display_decimal(start_total))  # Offer.pk =4 has a trial period
        self.assertEquals(get_display_decimal(remove_shirt_total), get_display_decimal(start_total - Offer.objects.get(pk=2).current_price()))

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
        recurring_offer = Offer.objects.get(pk=4)
        
        self.assertEquals(self.existing_invoice.get_recurring_total(), recurring_offer.current_price())

    def test_get_recurring_total_only_recurring_order_items(self):
        recurring_offer = Offer.objects.get(pk=5)
        
        self.assertEquals(self.new_invoice.get_recurring_total(), recurring_offer.current_price())
        self.assertEquals(self.new_invoice.get_one_time_transaction_total(), 0)

    def test_get_one_time_transaction_total_with_recurring_offer(self):
        recurring_offer = Offer.objects.get(pk=5)
        self.existing_invoice.update_totals()
        self.existing_invoice.save()
        before_total = self.existing_invoice.total
        before_one_time_total = get_display_decimal(self.existing_invoice.get_one_time_transaction_total())
        self.existing_invoice.add_offer(recurring_offer)
        after_total = self.existing_invoice.total
        after_one_time_total = get_display_decimal(self.existing_invoice.get_one_time_transaction_total())

        self.assertEquals(before_one_time_total, after_one_time_total)
        self.assertEquals(before_total, after_total)

    def test_get_one_time_transaction_total_no_recurring_order_items(self):
        self.existing_invoice.update_totals()

        self.assertEquals(self.existing_invoice.get_one_time_transaction_total(), (self.existing_invoice.total - self.existing_invoice.get_recurring_total()))
        self.assertEquals(get_display_decimal(self.existing_invoice.get_recurring_total()), get_display_decimal(self.existing_invoice.total - self.existing_invoice.get_one_time_transaction_total()))

    def test_get_recurring_order_items(self):
        before_count = self.existing_invoice.get_recurring_order_items().count()
        recurring_offer = Offer.objects.get(pk=5)
        self.existing_invoice.add_offer(recurring_offer)
        after_count = self.existing_invoice.get_recurring_order_items().count()

        self.assertNotEquals(before_count, after_count)

    def test_get_one_time_transaction_order_items(self):
        recurring_offer = Offer.objects.get(pk=5)
        self.existing_invoice.add_offer(recurring_offer)

        self.assertEquals(self.existing_invoice.get_one_time_transaction_order_items().count(), self.existing_invoice.order_items.all().count() - len(self.existing_invoice.get_recurring_order_items()))

    def test_empty_cart(self):
        self.assertNotEqual(0, self.existing_invoice.order_items.count())
        self.existing_invoice.empty_cart()
        self.assertEqual(0, self.existing_invoice.order_items.count())

    def test_empty_cart_in_checkout_state(self):
        self.existing_invoice.status = InvoiceStatus.CHECKOUT
        self.existing_invoice.save()
        self.assertNotEqual(0, self.existing_invoice.order_items.count())
        self.existing_invoice.empty_cart()
        self.assertEqual(0, self.existing_invoice.order_items.count())

    def test_swap_offers_success(self):
        hulk_offer = Offer.objects.get(pk=4)
        free_hulk_offer = Offer.objects.get(pk=5)
        self.new_invoice.add_offer(hulk_offer)
        self.new_invoice.swap_offer(hulk_offer, free_hulk_offer)
        self.assertFalse(self.new_invoice.order_items.filter(offer=hulk_offer).exists())
        self.assertTrue(self.new_invoice.order_items.filter(offer=free_hulk_offer).exists())

    def test_swap_offers_fail_no_matching_products(self):
        hulk_offer = Offer.objects.get(pk=4)
        cheese_offer = Offer.objects.get(pk=2)
        self.new_invoice.add_offer(hulk_offer)
        self.new_invoice.swap_offer(hulk_offer, cheese_offer)
        self.assertFalse(self.new_invoice.order_items.filter(offer=cheese_offer).exists())
        self.assertTrue(self.new_invoice.order_items.filter(offer=hulk_offer).exists())

    def test_invoice_no_discounts(self):
        self.new_invoice.add_offer(Offer.objects.get(pk=3))
        self.assertEqual(self.new_invoice.get_discounts(), 0)
        self.assertGreater(self.new_invoice.total, 0)

    def test_invoice_with_discounts_ten_off(self):
        discount = 10
        wheel_offer = Offer.objects.get(pk=3)
        wheel_price = Price.objects.get(pk=5)
        wheel_price.cost = wheel_offer.get_msrp() - discount
        wheel_price.save()
        self.new_invoice.add_offer(wheel_offer)
        self.assertGreater(wheel_offer.get_msrp(), self.new_invoice.total)
        self.assertEqual(self.new_invoice.get_discounts(), discount)

    def test_invoice_with_trial_discounts(self):
        free_month_offer = Offer.objects.get(pk=7)
        discount = free_month_offer.current_price()
        self.new_invoice.add_offer(free_month_offer)
        self.assertEqual(self.new_invoice.get_discounts(), discount)
        self.assertEqual(self.new_invoice.total, 0)

    def test_invoice_with_discount_and_trial_discounts(self):
        discount = 10
        wheel_offer = Offer.objects.get(pk=3)
        wheel_price = Price.objects.get(pk=5)
        wheel_price.cost = wheel_offer.get_msrp() - discount
        wheel_price.save()
        free_month_offer = Offer.objects.get(pk=7)
        trial_discount = free_month_offer.current_price()
        self.new_invoice.add_offer(free_month_offer)
        self.new_invoice.add_offer(wheel_offer)
        self.assertEqual(self.new_invoice.get_discounts(), discount + trial_discount)

    def test_save_discounts_vendor_notes(self):
        free_month_offer = Offer.objects.get(pk=7)
        discount = free_month_offer.current_price() - free_month_offer.get_trial_amount()
        self.new_invoice.add_offer(free_month_offer)
        self.new_invoice.save_discounts_vendor_notes()
        self.assertEqual(self.new_invoice.vendor_notes['discounts'], discount)

    def test_order_item_price_msrp(self):
        wheel_offer = Offer.objects.get(pk=3)
        self.new_invoice.add_offer(wheel_offer)
        self.assertEqual(self.new_invoice.order_items.first().price, wheel_offer.get_msrp())
        self.assertNotEqual(self.new_invoice.order_items.first().price, wheel_offer.current_price())

    def test_order_item_price_current_price(self):
        free_month = Offer.objects.get(pk=7)
        self.new_invoice.add_offer(free_month)
        self.assertNotEqual(self.new_invoice.order_items.first().price, free_month.get_msrp())
        self.assertEqual(self.new_invoice.order_items.first().price, free_month.current_price())

    def test_order_item_with_discounts(self):
        discount = 10
        wheel_offer = Offer.objects.get(pk=3)
        wheel_price = Price.objects.get(pk=5)
        wheel_price.cost = wheel_offer.get_msrp() - discount
        wheel_price.save()
        self.new_invoice.add_offer(wheel_offer)
        self.assertEqual(self.new_invoice.order_items.first().discounts, discount)

    def test_order_item_no_discounts(self):
        wheel_offer = Offer.objects.get(pk=3)
        self.new_invoice.add_offer(wheel_offer)
        self.assertEqual(self.new_invoice.order_items.first().discounts, 0)

    def test_order_item_with_trial_amount(self):
        free_month = Offer.objects.get(pk=7)
        discount = free_month.current_price()
        self.new_invoice.add_offer(free_month)
        self.assertEqual(self.new_invoice.order_items.first().trial_amount, free_month.current_price() - discount)

    def test_order_item_no_trial_amount(self):
        month_offer = Offer.objects.get(pk=6)
        self.new_invoice.add_offer(month_offer)
        self.assertEqual(self.new_invoice.get_recurring_total(), month_offer.current_price())
        self.assertEqual(self.new_invoice.get_discounts(), 0)
        self.assertEqual(self.new_invoice.order_items.first().trial_amount, month_offer.current_price())

    def test_invoice_global_discount(self):
        month_offer = Offer.objects.get(pk=6)
        self.new_invoice.add_offer(month_offer)
        self.new_invoice.global_discount = 10
        self.new_invoice.update_totals()
        self.new_invoice.save()
        self.assertEqual(self.new_invoice.total, month_offer.current_price() - self.new_invoice.global_discount)

    def test_invoice_negative_global_discount(self):
        month_offer = Offer.objects.get(pk=6)
        self.new_invoice.add_offer(month_offer)
        self.new_invoice.global_discount = -10
        self.new_invoice.update_totals()
        self.new_invoice.save()
        self.assertEqual(self.new_invoice.total, month_offer.current_price() + self.new_invoice.global_discount)
    
    def test_invoice_global_discount_no_less_than_zero(self):
        month_offer = Offer.objects.get(pk=6)
        self.new_invoice.add_offer(month_offer)
        self.new_invoice.global_discount = 101
        self.new_invoice.update_totals()
        self.new_invoice.save()
        self.assertEqual(self.new_invoice.total, 0)

    def test_get_promos(self):
        invoice = Invoice.objects.get(pk=1)

        self.assertNotEquals(invoice.get_promos(), "")

    def test_get_promos_none(self):
        self.assertEquals(self.new_invoice.get_promos(), "")

    def test_get_promos_empty(self):
        self.new_invoice.vendor_notes['promos'] = {}
        self.new_invoice.save()
        self.assertEquals(self.new_invoice.get_promos(), "")

    def test_soft_delete(self):
        invoice = Invoice.objects.all().first()
        invoice_count_before_deletion = Invoice.objects.all().count()
        invoice.delete()

        deleted_invoice_difference = Invoice.objects.all().count() - Invoice.not_deleted.count()

        self.assertEqual(Invoice.objects.all().count() - deleted_invoice_difference, Invoice.not_deleted.count())
        self.assertEquals(invoice_count_before_deletion, Invoice.objects.all().count())

    def test_get_next_billing_date_month(self):
        pass

    def test_get_next_billing_price(self):
        pass

    def test_clear_promos_when_last_item_is_removed(self):
        ...
        pass
    

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

        self.assertContains(response, f'<span>${self.invoice.calculate_subtotal():.2f}</span>')
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

        add_mug_url = reverse("vendor_api:add-to-cart", kwargs={'slug': self.mug_offer.slug})
        self.client.post(add_mug_url)
        self.assertContains(response, f'<span class="text-primary">${self.invoice.total}</span>')

        remove_shirt_url = reverse("vendor_api:remove-from-cart", kwargs={'slug': self.shirt_offer.slug})
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
        self.assertRedirects(response, reverse('account_login') + '?next=' + self.view_url )

    def test_cost_overview_discounts(sefl):
        pass

    def test_cost_overview_no_discounts(self):
        pass

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

    def test_view_redirect_login(self):
        self.client.logout()
        response = self.client.get(self.view_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_login') + '?next=' + self.view_url )

    def test_view_missing_data(self):
        session = self.client.session
        session['billing_address_form'] = BillingAddressForm().initial
        session['credit_card_form'] = CreditCardForm().initial
        session.save()
        self.invoice.status = InvoiceStatus.CHECKOUT
        self.invoice.save()

        response = self.client.post(self.view_url)

        self.assertRedirects(response, reverse('vendor:checkout-account'))

    def test_view_payment_success(self):
        self.invoice.status = InvoiceStatus.CHECKOUT
        self.invoice.save()
        Payment.objects.all().delete()
        form_data = {
            'billing_address_form': {
                'billing-name': 'Home',
                'billing-company': 'Whitemoon Dreams',
                'billing-country': 840,
                'billing-address_1': '221B Baker Street',
                'billing-address_2': '',
                'billing-locality': 'Marylebone',
                'billing-state': 'California',
                'billing-postal_code': '90292'},
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
        session['billing_address_form'] = { f'billing-{key}': value for key, value in billing_address.cleaned_data.items() }
        session['credit_card_form'] = payment_info.cleaned_data
        session.save()

        response = self.client.post(self.view_url)

        self.assertEquals(self.invoice.payments.all().count(), Payment.objects.filter(invoice=self.invoice).count())
    
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
        self.assertRedirects(response, reverse('account_login') + '?next=' + self.view_url)

    def test_cost_overview_discounts(self):
        pass

    def test_cost_overview_no_discounts(self):
        pass
