# Generated by Django 3.1.3 on 2021-06-02 15:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_default_user():
    """
    Function will return the value for MIGRATION_0023_DEFAULT_USER declared in the
    the settings.py file. If the constant is not declared or is None it will return
    1 to be set as a default value.
    """
    if hasattr(settings, 'MIGRATION_0023_DEFAULT_USER') and settings.MIGRATION_0023_DEFAULT_USER is not None:
        return settings.MIGRATION_0023_DEFAULT_USER
    return 1


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vendor', '0022_offer_meta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerprofile',
            name='user',
            field=models.ForeignKey(default=set_default_user, on_delete=django.db.models.deletion.CASCADE, related_name='customer_profile', to='auth.user', verbose_name='User'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='profile',
            field=models.ForeignKey(default=set_default_user, on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='vendor.customerprofile', verbose_name='Customer Profile'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='payment',
            name='profile',
            field=models.ForeignKey(blank=True, default=set_default_user, on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='vendor.customerprofile', verbose_name='Purchase Profile'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='receipt',
            name='profile',
            field=models.ForeignKey(default=set_default_user, on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='vendor.customerprofile', verbose_name='Purchase Profile'),
            preserve_default=False,
        ),
    ]
