


from django.core.exceptions import ImproperlyConfigured
from django.contrib import messages
from django.utils.translation import ugettext as _




class ProductRequiredMixin(class):
    """
    Checks to see if a user has a required product and if not, redirects them.
    """

    product_queryset = None
    product_model = None
    product_slug_field = "product_slug"
    product_pk_url_kwarg = "pk"
    product_slug_url_kwarg = None
    product_redirect = "/"

    # Override the dispatcher on check?

    def get_product_slug_field(self):
        """Get the name of a slug field to be used to look up by slug."""
        return self.product_slug_field

    def get_product_queryset(self):
        if self.product_queryset is None:
            if self.product_model:
                return self.product_model._default_manager.all()
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a product QuerySet. Define "
                    "%(cls)s.product_model, %(cls)s.product_queryset, or override "
                    "%(cls)s.get_product_queryset()." % {
                        'cls': self.__class__.__name__
                    }
                )
        return self.product_queryset.all()

    def get_product(self, product_queryset=None):
        '''
        Get the product based on the settings.
        '''
        if product_queryset is None:
            product_queryset = self.get_product_queryset()

        pk = self.kwargs.get(self.product_pk_url_kwarg)
        slug = self.kwargs.get(self.product_slug_url_kwarg)

        if pk is not None:
            product_queryset = product_queryset.filter(pk=pk)

        # if self.product_slug_keyword:
        #     return self.product_model.object.get(slug=self.kwargs[self.product_slug_keyword])

        # if self.product_id_keyword:
        #     return self.product_model.object.get(pk=self.kwargs[self.product_id_keyword])

        return None

    def no_product_path(self):
        '''
        The result to be returned if no viable product is found
        if None is returned, use a 404 response.

        This method allows for a dynamic redirect to be used.
        Default is to use the product_redirect path.
        '''
        messages.info(self.request, _("Product Purchase required."))

        return self.product_redirect
