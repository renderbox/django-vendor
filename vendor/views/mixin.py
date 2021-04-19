from django.core.exceptions import ImproperlyConfigured
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from vendor.utils import get_site_from_request


class PassRequestToFormKwargsMixin:

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class ProductRequiredMixin:
    """
    Checks to see if a user has a required product and if not, redirects them.
    ProductRequiredMixin expects that request.site is set.
    """
    product_queryset = None
    product_model = None
    product_redirect = "/"
    product_owned = False

    def dispatch(self, request, *args, **kwargs):
        """
        Verify that the current user owns the product.  Checks on all HTTP methods.
        """
        if not self.user_has_product():
            return self.handle_no_product()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Variable set by ProductRequiredMixin
        context['product_owned'] = self.product_owned
        return context

    def user_has_product(self):
        """
        Check to see if a user has a viable product license based on the get_product_queryset() method.

        TODO: move this to some kind of caching or session variable to avoid hitting the DB on every request.
        """
        if self.request.user.is_anonymous:
            self.product_owned = False
        else:
            products = self.get_product_queryset()
            self.product_owned = self.request.user.customer_profile.filter(
                site=get_site_from_request(self.request)).get().has_product(products)

        return self.product_owned

    def get_product_queryset(self):
        """
        Method to get the Product(s) needed for the check.  Can be overridden to handle complex queries.
        """
        if self.product_queryset is None:
            if self.product_model:
                # Only provide list of products on the current site.
                return self.product_model.objects.filter(site=get_site_from_request(self.request))
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a Product QuerySet. Define "
                    "%(cls)s.product_model, %(cls)s.product_queryset, or override "
                    "%(cls)s.get_product_queryset()." % {
                        'cls': self.__class__.__name__
                    }
                )
        return self.product_queryset.all()

    def handle_no_product(self):
        '''
        The result to be returned if no viable product is found owned by the user.
        If None is returned, default to a 404 response.

        This method allows for a dynamic redirect to be used.
        Default is to use the product_redirect path.
        '''

        if not self.product_redirect:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': self.get_product_queryset().model._meta.verbose_name})

        messages.info(self.request, _("Product Purchase required."))
        return redirect(self.product_redirect)
