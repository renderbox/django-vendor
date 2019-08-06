from django.contrib import admin

# Register your models here.
from vendor.models import Catalog, Item

admin.site.register(Catalog)
admin.site.register(Item)
