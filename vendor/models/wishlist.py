
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .base import CreateUpdateModelBase

###########
# WISHLIST
###########

class Wishlist(models.Model):
    profile = models.ForeignKey("vendor.CustomerProfile", verbose_name=_("Purchase Profile"), null=True, on_delete=models.CASCADE, related_name="wishlists")
    name = models.CharField(_("Name"), max_length=100, blank=False)

    class Meta:
        verbose_name = "Wishlist"
        verbose_name_plural = "Wishlists"

    def __str__(self):
        return self.name

################
# WISHLIST ITEM
################

class WishlistItem(CreateUpdateModelBase):
    '''
    
    '''
    wishlist = models.ForeignKey(Wishlist, verbose_name=_("Wishlist"), on_delete=models.CASCADE, related_name="wishlist_items")
    offer = models.ForeignKey("vendor.Offer", verbose_name=_("Offer"), on_delete=models.CASCADE, related_name="wishlist_items")

    class Meta:
        verbose_name = "Wishlist Item"
        verbose_name_plural = "Wishlist Items"
        # TODO: Unique Name Per User

    def __str__(self):
        return "({}) {}: {}".format(self.wishlist.profile.user.username, self.wishlist.name, self.offer.name)
