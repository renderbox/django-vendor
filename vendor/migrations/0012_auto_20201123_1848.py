# Generated by Django 3.1.3 on 2020-11-23 18:48

from django.db import migrations, models
import vendor.models.offer


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0011_auto_20201120_1750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offer',
            name='offer_description',
            field=models.TextField(blank=True, default=None, help_text='You can enter a list of descriptions. Note: if you inputs something here the product description will not show up.', null=True, verbose_name='Offer Description'),
        ),
        migrations.AlterField(
            model_name='offer',
            name='term_details',
            field=models.JSONField(blank=True, default=vendor.models.offer.offer_term_details_default, help_text='term_units: 10/20(Day/Month), trial_occurrences: 1(defualt)', null=True, verbose_name='Term Details'),
        ),
    ]
