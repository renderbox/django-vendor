from django.contrib import admin

# Register your models here.
from core.models import Catalog, Product

admin.site.register(Product)
admin.site.register(Catalog)