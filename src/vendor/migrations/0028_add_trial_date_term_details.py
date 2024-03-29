# Generated by Django 3.1.14 on 2021-12-16 16:29

from django.db import migrations


def add_trial_day_key_offer_term_details(apps, schema_editor):
    OfferModel = apps.get_model('vendor', 'Offer')
    for offer in OfferModel.objects.all():
        if 'trial_days' not in offer.term_details:
            offer.term_details['trial_days'] = 0
            offer.save()


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0027_bugfix_vendor_notes_invoice_history'),
    ]

    operations = [
        migrations.RunPython(add_trial_day_key_offer_term_details, reverse_code=migrations.RunPython.noop),
    ]
