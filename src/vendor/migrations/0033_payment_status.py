# Generated by Django 3.2.13 on 2022-06-01 22:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0032_alter_invoice_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='status',
            field=models.IntegerField(choices=[(1, 'Queued'), (2, 'Active'), (10, 'Authorized'), (15, 'Captured'), (20, 'Settled'), (30, 'Canceled'), (35, 'Refunded'), (40, 'Declined'), (50, 'Void')], default=0, verbose_name='Status'),
        ),
    ]