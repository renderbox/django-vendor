from django.utils import timezone
from django.db.models import F
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist

from django.views import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.http import HttpResponse

from vendor.models import Offer, OrderItem, Invoice, Payment, Address
from vendor.models.address import Address as GoogleAddress
from vendor.processors import PaymentProcessor
from vendor.forms import BillingAddressForm, CreditCardForm

from .vendor_admin import AdminDashboardView, AdminInvoiceDetailView, AdminInvoiceListView


payment_processor = PaymentProcessor              # The Payment Processor configured in settings.py

# class CartView(LoginRequiredMixin, DetailView):
#     '''
#     View items in the cart
#     '''
#     model = Invoice

#     def get_object(self):
#         profile, created = self.request.user.customer_profile.get_or_create(site=settings.SITE_ID)
#         return profile.get_cart()


# class AddToCartView(LoginRequiredMixin, TemplateView):
#     '''
#     Create an order item and add it to the order
#     '''

#     def get(self, *args, **kwargs):         # TODO: Move to POST
#         offer = Offer.objects.get(slug=self.kwargs["slug"])
#         profile, created = self.request.user.customer_profile.get_or_create(site=settings.SITE_ID)      # Make sure they have a cart

#         cart = profile.get_cart()
#         cart.add_offer(offer)

#         messages.info(self.request, _("Added item to cart."))

#         return redirect('vendor:cart')      # Redirect to cart on success


# class RemoveFromCartView(LoginRequiredMixin, DeleteView):
#     '''
#     Reduce the count of items from the cart and delete the order item if you reach 0
#     TODO: Change to form/POST for better security & flexibility
#     '''
#     def get(self, *args, **kwargs):         # TODO: Move to POST
#         offer = Offer.objects.get(slug=self.kwargs["slug"])

#         profile = self.request.user.customer_profile.get(site=settings.SITE_ID)      # Make sure they have a cart
#         cart = profile.get_cart()
#         cart.remove_offer(offer)

#         messages.info(self.request, _("Removed item from cart."))

#         return redirect('vendor:cart')      # Redirect to cart on success


# class PaymentView(LoginRequiredMixin, TemplateView):
#     '''
#     Review items and submit Payment
#     '''
#     template_name = "vendor/checkout.html"
#     # billing_address_form_class = BillingAddressForm
#     # card_form_class = CreditCardForm
#     # payment_processor = PaymentProcessor

#     # def get_context_data(self, **kwargs):
#     #     context = super().get_context_data(**kwargs)

#     #     profile = self.request.user.customer_profile.get(site=settings.SITE_ID) 
#     #     invoice = profile.invoices.get(status=Invoice.InvoiceStatus.CART)

#     #     processor = self.payment_processor(invoice)

#     #     context = processor.get_checkout_context(context=context)

#     #     context['billing_form'] = self.billing_form_class()
#     #     # TODO: Set below in the PaymentProcessor Context. It should set the address form and card form?
#     #     context['address_form'] = self.address_form_class(prefix='addr')
#     #     context['card_form'] = self.card_form_class(prefix='card')

#     #     return context

#     def get(self, request, *args, **kwargs):
#         context = super().get_context_data(**kwargs)
#         profile = self.request.user.customer_profile.get(site=settings.SITE_ID) 
#         invoice = profile.invoices.get(status=Invoice.InvoiceStatus.CART)

#         processor = payment_processor(invoice)

#         context = processor.get_checkout_context(context=context)

#         return render(request, self.template_name, context)


#     def post(self, request, *args, **kwargs):
#         context = super().get_context_data(**kwargs)
#         profile = request.user.customer_profile.get(site=settings.SITE_ID) 
#         invoice = Invoice.objects.get(profile=profile, status=Invoice.InvoiceStatus.CART)
                
#         credit_card_form = CreditCardForm(request.POST, prefix='credit-card')
#         billing_address_form = BillingAddressForm(request.POST, prefix='billing-address')
        
#         if not (billing_address_form.is_valid() or credit_card_form.is_valid()):
#             return render(request, self.template_name, processor.get_checkout_context(context))
        
#         processor = payment_processor(invoice)

#         processor.process_payment(request)
#         if processor.transaction_submitted:
#             return redirect('vendor:purchase-summary', pk=invoice.pk)   # redirect to the summary page for the above invoice
#             # TODO: invoices should have a UUID attached to them
#             # return redirect('vendor:purchase-summary', pk=processor.invoice.payments.filter(success=True).values_list('pk'))    # TODO: broken
#         else:
#             return render(request, self.template_name, processor.get_checkout_context(request, context))

        
# class PaymentView(LoginRequiredMixin, DetailView):
#     model = Payment


######################
# Order History Views

class OrderHistoryListView(LoginRequiredMixin, ListView):
    '''
    List of all the invoices generated by the current user on the current site.
    '''
    model = Invoice
    #TODO: filter to only include the current user's order history

    def get_queryset(self):
        try:
            return self.request.user.customer_profile.get().invoices.filter(status__gt=Invoice.InvoiceStatus.CART)  # The profile and user are site specific so this should only return what's on the site for that user excluding the cart
        except ObjectDoesNotExist:         # Catch the actual error for the exception
            return []   # Return empty list if there is no customer_profile

class OrderHistoryDetailView(LoginRequiredMixin, DetailView):
    '''
    Details of an invoice generated by the current user on the current site.
    '''
    template_name = "vendor/invoice_history_detail.html"
    model = Invoice
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'


# class PaymentView(LoginRequiredMixin, TemplateView):
# class PaymentView(TemplateView):
#     '''
#     Review items and submit Payment
#     '''
#     template_name = "vendor/checkout.html"

#     # GET returns the invoice with the items and the estimated totals.

#     def get(self, request, *args, **kwargs):
#         profile = request.user.customer_profile.get(site=settings.SITE_ID)      # Make sure they have a cart
#         order = Invoice.objects.get(profile=profile, status=0)

#         ctx = payment_processor.get_checkout_context(order, customer_id=str(request.user.pk))
#         print(ctx)

#         return render(request, self.template_name, ctx)


#     def post(self, request, *args, **kwargs):
#         print(request)
#         print(request.POST)
#         print(request.headers)
#         profile = request.user.customer_profile.get(site=settings.SITE_ID)      # Make sure they have a cart
#         order = Invoice.objects.get(profile=profile, status=0)
#         token = request.POST.get("stripeToken")

#         # amount= int(order.total * 100)
#         # currency = order.currency

#         # description = "Invoice #{} for ... in the amount of {}".format(order.pk, amount)

#         # # stripe.Charge.create(
#         # #     amount=amount,
#         # #     currency=currency,
#         # #     source=token,
#         # #     description=description,
#         # # )

#         # order.status = 20




# class NewAddToCartView(CreateView):
#     model = OrderItem
#     form_class = AddToCartModelForm                                                         # todo: Move to a regular Form from a ModelForm since the advantages of the ModelForm are not used...
#     success_url = reverse_lazy('vendor-user-cart-retrieve')

#     def form_valid(self, form):

#         invoice, invoice_created = self.request.user.invoice_set.get_or_create(status=OrderStatus.CART.value)   # todo: Need to see if there is a way to make sure there is a cart and handle the theoretical case of multiples (thought it should be a 'singleton').

#         quantity = form.instance.quantity                                                               # How many?
#         offer = Offer.objects.get( sku=self.kwargs['sku'] )                                             # SKU is in the URL...

#         order_item, created = invoice.order_items.get_or_create(offer=offer)                            # Get or Create an order item with the matching values

#         if not created:                                                                                 # Add the quantity if it already exists
#             order_item.quantity += quantity
#         else:                                                                                           # Set the value if it does not
#             order_item.quantity = quantity

#         order_item.save()
#         messages.info(self.request, "\"{}\"".format( order_item.product_name ) + _(" added to cart."))

#         return redirect(self.success_url)


# class AddToCartView(LoginRequiredMixin, CreateView):
#     model = OrderItem
#     form_class = AddToCartModelForm
#     success_url = reverse_lazy('vendor-user-cart-retrieve')

#     # def get_object(self, queryset=None):
#     #     self.offer = self.request.POST.get('offer')         # todo: This is meant to return a model object, not a string...
#     #     return self.offer

#     def form_valid(self,form):
#         # offer = Offer.objects.get(id = self.get_object()) 
#         offer = Offer.objects.get(sku=self.request.POST.get('offer') ) 
    
#         price = offer.current_price() #sale_price.filter(start_date__lte= timezone.now(), end_date__gte=timezone.now()).order_by('priority').first()

#         invoice = Invoice.objects.filter(user = self.request.user, status=OrderStatus.CART.value)

#         # check if there is an invoice with status= cart for the user
#         if invoice.exists():

#             invoice_qs = invoice[0]

#             order_item = invoice_qs.order_items.filter(offer__sku = offer.sku)

#             # check if the order_item is there in the invoice, if yes increase the quantity
#             if order_item.exists():
#                 order_item.update(quantity=F('quantity')+1)
#                 messages.info(self.request, _("Item quantity was updated."))
#                 return redirect(self.success_url)

#             # Create an order_item object for the invoice
#             else:
#                 order_item = self.model.objects.create(
#                     invoice = invoice_qs,
#                     offer=offer,
#                     price=price
#                 )
#                 messages.info(self.request, _("Item added to cart."))
#                 return redirect(self.success_url)

#         # Create a invoice object with status = cart
#         else:
#             ordered_date = timezone.now()
#             invoice = Invoice.objects.create(user=self.request.user, ordered_date=ordered_date)

#             order_item = OrderItem.objects.create(invoice = invoice, offer = offer, price = price)
#             messages.info(self.request, _("Item added to cart."))
#             return redirect(self.success_url)


# class RetrieveCartView(LoginRequiredMixin, ListView):
#     model = Invoice

#     def get_queryset(self):
#         invoice = self.model.objects.filter(user = self.request.user, status=OrderStatus.CART.value).first()
#         if invoice:
#             return invoice.order_items.all()

#         return None

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         count = 0
#         invoice = self.model.objects.filter(user = self.request.user, status=OrderStatus.CART.value)
#         if invoice:
#             context['invoice'] = True

#         if self.get_queryset():
#             for item in self.get_queryset():
#                 count += item.quantity

#             context['item_count'] = count
        
#         return context

# class RemoveFromCartView(LoginRequiredMixin, DeleteView):
#     model = OrderItem
#     success_url = reverse_lazy('vendor-user-cart-retrieve')

#     def get_object(self, queryset=None):
#         invoice = Invoice.objects.get(user = self.request.user, status=OrderStatus.CART.value)
#         return invoice.order_items.get(offer__sku = self.kwargs['sku'])

#     def form_valid(self, form):
#         self.get_object().delete()
#         messages.info(self.request, _("Item removed from cart"))
#         return redirect(self.success_url)


# class CartItemQuantityEditView(LoginRequiredMixin, View):
  
#     def post(self, request, *args, **kwargs):

#         quantity = request.POST.get('quantity')

#         order_item = OrderItem.objects.filter(id = self.kwargs['id']).update(quantity = quantity )  

#         return redirect(reverse_lazy('vendor-user-cart-retrieve'))

         
# class DeleteCartView(LoginRequiredMixin, DeleteView):
#     model = Invoice

#     def delete(request):

#         invoice = self.model.filter(user = request.user, status = 0)

#         if invoice:
#             invoice[0].order_items.all().delete()
#             invoice[0].delete()

#             messages.info(request, "User Cart deleted.")
#             return redirect("vendor:vendor_index")

#         else:
#             messages.info(request, "You do not have an active cart.")
#             return redirect("vendor:vendor_index")


# class RetrieveOrderSummaryView(LoginRequiredMixin, ListView):
#     model = Invoice
#     template_name = "vendor/ordersummary.html"

#     def get_queryset(self):
#         invoice = self.model.objects.get(user = self.request.user, status=OrderStatus.CART.value)
#         return invoice.order_items.all()

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         count = 0
#         total = 0
    
#         for item in self.get_queryset():
#             count +=  item.quantity
#             total += item.total

#         context['item_count'] = count
#         context['order_total'] = total
#         context['amount'] = total * 100
#         context['key'] = settings.STRIPE_TEST_PUBLIC_KEY
        
#         return context


# class PaymentProcessingView(LoginRequiredMixin, View):

#     def post(self, *args, **kwargs):
#         stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
#         token = self.request.POST['stripeToken']

#         invoice = Invoice.objects.get(user = self.request.user, status=OrderStatus.CART.value)

#         total = 0
        
#         order_items = invoice.order_items.all()

#         for item in order_items:
#             total += item.total

#         try:
#             customer_profile = CustomerProfile.objects.get(user = self.request.user)
        
#         except:
#             customer_profile = CustomerProfile.objects.create(user = self.request.user, currency = 'usd', attrs = {})
        
#         stripe_customer_id = customer_profile.attrs.get('stripe_customer_id', None)

#         if stripe_customer_id != '' and stripe_customer_id is not None:
#                     customer = stripe.Customer.retrieve(
#                         stripe_customer_id)

#         else:
#             customer = stripe.Customer.create(
#                 email=self.request.user.email,
#                 card=token
#             )
#             customer_profile.attrs['stripe_customer_id'] = customer['id']
#             customer_profile.save()
     
#         charge = stripe.Charge.create(
#             amount=int(total * 100),
#             currency='usd',
#             description='TrainingCamp Charge',      # todo: this need to be set relative to the offer item.
#             customer=customer.id,
#             metadata={'invoice_id': invoice.id},
#         )

#         invoice.status = OrderStatus.COMPLETE.value
#         invoice.attrs = {'charge': charge.id}
#         invoice.ordered_date = timezone.now()
#         invoice.save()

#         for items in order_items:
#             Purchase.objects.create(order_item = items, product = items.offer.product, user = self.request.user)
        
#         messages.success(self.request, _("Your order was successful!"))
#         return redirect(reverse_lazy('vendor-user-order-retrieve', kwargs = {'id': invoice.id}))


# class RetrieveOrderView(LoginRequiredMixin, ListView):
#     model = Purchase

#     def get_queryset(self):
#         return self.model.objects.filter(order_item__invoice__id = self.kwargs['id'])


# class RetrievePurchaseView(LoginRequiredMixin, DetailView):
#     model = Purchase

#     def get_object(self):
#         return self.model.objects.get(id=self.kwargs['id'])

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)

#         status = self.get_object().status

#         if status is PurchaseStatus.ACTIVE.value or status is PurchaseStatus.QUEUED.value:
#             context['refund'] = "Request Refund"
#             context['active'] = True

#         elif status is PurchaseStatus.CANCELED.value:
#             context['refund'] = "Refund Requested"

#         elif status is PurchaseStatus.REFUNDED.value:
#             context['refund'] = "Refund Issued"

#         return context


# class RetrievePurchaseListView(LoginRequiredMixin, ListView):
#     model = Purchase 

#     def get_queryset(self):
#         return self.request.user.purchase_set.all()

       
# class RequestRefundView(LoginRequiredMixin, CreateView):
#     model = Refund
#     form_class = RequestRefundForm

#     def get_object(self, queryset=None):
#         self.purchase = Purchase.objects.get(id=self.kwargs['id'])
#         return self.purchase

#     def form_valid(self,form):

#         purchase = self.get_object()

#         reason = self.request.POST.get('reason')

#         Refund.objects.create(purchase = purchase, reason = reason, user = self.request.user)

#         purchase.status = PurchaseStatus.CANCELED.value
#         purchase.save()

#         messages.info(self.request, _("Refund request created"))
#         return redirect(reverse_lazy('vendor-user-purchase-list'))


# # class RetrieveRefundRequestsView(LoginRequiredMixin, ListView):
# #     model = Refund 

# #     def get_queryset(self):
# #         return self.model.objects.all()


# class IssueRefundView(LoginRequiredMixin, CreateView):
#     model = Refund 
#     success_url = reverse_lazy('vendor-retrieve-refund-requests')

#     def get_queryset(self):
#         return self.model.objects.get(id = self.kwargs['id'])

#     def post(self, request, *args, **kwargs):
#         stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
        
#         refund = self.get_queryset()
#         purchase = refund.purchase

#         invoice = purchase.order_item.invoice 

#         charge = invoice.attrs['charge']

#         stripe.Refund.create(
#             charge=charge, amount = int(purchase.order_item.price.cost * 100))

#         refund.accepted = True
#         refund.save()

#         purchase.status = PurchaseStatus.REFUNDED.value
#         purchase.save()

#         messages.info(request, _("Refund was issued"))

#         return redirect(reverse_lazy('vendor-retrieve-refund-requests'))





   

  
