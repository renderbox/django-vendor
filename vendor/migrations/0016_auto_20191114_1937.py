# Generated by Django 2.2.7 on 2019-11-14 19:37

from django.db import migrations, models
import vendor.models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0015_auto_20191114_1834'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.IntegerField(choices=[(vendor.models.OrderStatus(0), 'Cart'), (vendor.models.OrderStatus(10), 'Processing'), (vendor.models.OrderStatus(20), 'Complete')], default=0, verbose_name='Status'),
        ),
        migrations.AlterField(
            model_name='purchase',
            name='status',
            field=models.IntegerField(choices=[(vendor.models.PurchaseStatus(0), 'Queued'), (vendor.models.PurchaseStatus(10), 'Active'), (vendor.models.PurchaseStatus(20), 'Expired'), (vendor.models.PurchaseStatus(30), 'Canceled'), (vendor.models.PurchaseStatus(40), 'Refunded'), (vendor.models.PurchaseStatus(50), 'Completed')], default=0, verbose_name='Status'),
        ),
    ]
