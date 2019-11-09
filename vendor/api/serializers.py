# --------------------------------------------
# Copyright 2019, Grant Viklund
# @Author: Grant Viklund
# @Date:   2019-07-22 18:25:42
# --------------------------------------------

from rest_framework import serializers, fields

from vendor.models import Offer, Price, Purchase, Invoice, OrderItem
from core.models import Product


class AddToCartSerializer(serializers.ModelSerializer):
    offer = serializers.SlugRelatedField(slug_field='sku', queryset=Offer.objects.all())

    class Meta:
        model = OrderItem
        fields = ('offer',)


class RefundRequestSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Purchase
        fields = ('order_item',)

