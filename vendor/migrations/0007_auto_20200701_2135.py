# Generated by Django 3.0.7 on 2020-07-01 21:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0006_auto_20200630_0255'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='customer_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='vendor_notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]
