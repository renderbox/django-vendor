# Generated by Django 3.2.15 on 2022-09-01 12:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0038_auto_20220719_0944'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerprofile',
            name='meta',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Meta'),
        ),
    ]
