# Generated by Django 3.1.3 on 2020-12-08 18:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_auto_20201123_1848'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='reciepts',
            new_name='receipts',
        ),
    ]