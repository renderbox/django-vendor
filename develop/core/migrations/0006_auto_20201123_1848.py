# Generated by Django 3.1.3 on 2020-11-23 18:48

from django.db import migrations, models
import vendor.models.base


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20201118_2237'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='description',
            field=models.JSONField(blank=True, default=vendor.models.base.product_description_default, help_text="Eg: {'call out': 'The ultimate product'}", null=True, verbose_name='Description'),
        ),
    ]