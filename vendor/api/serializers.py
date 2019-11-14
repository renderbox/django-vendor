# --------------------------------------------
# Copyright 2019, Grant Viklund
# @Author: Grant Viklund
# @Date:   2019-07-22 18:25:42
# --------------------------------------------

from rest_framework import serializers, fields

from vendor.models import Offer, Price, Purchase, Invoice, OrderItem, Refund
from core.models import Product


class AddToCartSerializer(serializers.ModelSerializer):
    offer = serializers.SlugRelatedField(slug_field='sku', queryset=Offer.objects.all())

    class Meta:
        model = OrderItem
        fields = ('offer',)


class RefundRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = Refund
        fields = ('purchase', 'reason')


class RefundIssueSerializer(serializers.ModelSerializer):

    class Meta:
        model = Refund
        fields = ('purchase', 'reason', 'accepted')
        read_only_fields = ('purchase', 'reason', 'accepted')

