from django.utils.translation import ugettext as _
from django.db import models

from vendor.models import ProductBase

##########
# CATALOG
##########

class Catalog(models.Model):
    '''
    An Example Catalog use for Development
    '''
    name = models.CharField(_("Name"), max_length=80, blank=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=settings.SITE_ID)

    def __str__(self):
        return self.name

##########
# PRODUCT
##########

class Product(ProductBase):
    '''
    An Example Product use for Development
    '''
    name = models.CharField(_("Name"), max_length=80, blank=True)
    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name="products")




'''
# Product Download From S3 with expiring token
# https://www.gyford.com/phil/writing/2012/09/26/django-s3-temporary/

from django import http
from django.shortcuts import get_object_or_404
from django.views.generic import RedirectView

from boto.s3.connection import S3Connection

from yourproject.yourapp.models import MyModel

logger = getLogger('django.request')

class SecretFileView(RedirectView):
    permanent = False

    get_redirect_url(self, **kwargs):
        s3 = S3Connection(settings.AWS_ACCESS_KEY_ID,
                            settings.AWS_SECRET_ACCESS_KEY,
                            is_secure=True)
        # Create a URL valid for 60 seconds.
        return s3.generate_url(60, 'GET',
                            bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            key=kwargs['filepath'],
                            force_http=True)

    def get(self, request, *args, **kwargs):
        m = get_object_or_404(MyModel, pk=kwargs['pk'])
        u = request.user

        if u.is_authenticated() and (u.get_profile().is_very_special() or u.is_staff):
            if m.private_file:
                filepath = settings.MEDIA_DIRECTORY + m.private_file
                url = self.get_redirect_url(filepath=filepath)
                # The below is taken straight from RedirectView.
                if url:
                    if self.permanent:
                        return http.HttpResponsePermanentRedirect(url)
                    else:
                        return http.HttpResponseRedirect(url)
                else:
                    logger.warning('Gone: %s', self.request.path,
                                extra={
                                    'status_code': 410,
                                    'request': self.request
                                })
                    return http.HttpResponseGone()
            else:
                raise http.Http404
        else:
            raise http.Http404
'''