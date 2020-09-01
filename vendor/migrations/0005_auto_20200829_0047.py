# Generated by Django 3.1 on 2020-08-29 00:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0004_auto_20200828_2126'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payee_company',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Company'),
        ),
        migrations.AddField(
            model_name='payment',
            name='payee_full_name',
            field=models.CharField(default='Ellen Johnson', max_length=50, verbose_name='Name on Card'),
            preserve_default=False,
        ),
    ]