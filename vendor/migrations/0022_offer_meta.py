# Generated by Django 3.1.3 on 2021-04-28 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0021_auto_20210408_2303'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='meta',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Meta'),
        ),
    ]
