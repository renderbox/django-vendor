# Generated by Django 3.1.3 on 2021-09-14 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0025_auto_20210914_0025'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='Deleted'),
        ),
        migrations.AddField(
            model_name='payment',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='Deleted'),
        ),
        migrations.AddField(
            model_name='receipt',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='Deleted'),
        ),
    ]
