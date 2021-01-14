# Generated by Django 3.1.3 on 2021-01-07 23:10

from django.db import migrations

import uuid

def generate_address_uuid(apps, schema_editor):
    AddressModel = apps.get_model('vendor', 'Address')
    for address in AddressModel.objects.all():
        address.uuid = uuid.uuid4()
        address.save(update_fields=['uuid'])

def generate_customer_profile_uuid(apps, schema_editor):
    CustomerProfileModel = apps.get_model('vendor', 'CustomerProfile')
    for customer_profile in CustomerProfileModel.objects.all():
        customer_profile.uuid = uuid.uuid4()
        customer_profile.save(update_fields=['uuid'])

class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0018_add_uuid_address_profile'),
    ]

    operations = [
        migrations.RunPython(generate_address_uuid, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(generate_customer_profile_uuid, reverse_code=migrations.RunPython.noop),
    ]
