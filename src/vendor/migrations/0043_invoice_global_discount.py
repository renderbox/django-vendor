# Generated by Django 3.2.19 on 2023-05-09 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0042_offer_is_promotional'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='global_discount',
            field=models.FloatField(blank=True, default=0, null=True, verbose_name='Global Discount'),
        ),
    ]
