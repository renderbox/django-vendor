# Generated by Django 3.2.13 on 2022-06-01 17:45

from django.db import migrations


def pre_invoice_status_change(apps, schema_editor):
    InvoiceModel = apps.get_model('vendor', 'Invoice')

    print(f"Invoice Status Updating {InvoiceModel.objects.filter(status__gt=10).count()}")
    InvoiceModel.objects.filter(status__gt=10).update(status=20)
    print(f"Invoice Status Updated {InvoiceModel.objects.filter(status__gt=10).count()}")


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0030_auto_20220414_1055'),
    ]

    operations = [
        migrations.RunPython(pre_invoice_status_change, reverse_code=migrations.RunPython.noop),
    ]
