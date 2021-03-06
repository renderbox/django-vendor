# Generated by Django 3.1.1 on 2020-09-10 22:06

import autoslug.fields
from django.conf import settings
import django.contrib.sites.managers
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
import uuid

from vendor.config import VENDOR_PRODUCT_MODEL

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(VENDOR_PRODUCT_MODEL),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, default='Home', max_length=80, verbose_name='Address Name')),
                ('address_1', models.CharField(max_length=40, verbose_name='Address 1')),
                ('address_2', models.CharField(blank=True, max_length=40, null=True, verbose_name='Address 2')),
                ('locality', models.CharField(max_length=40, verbose_name='City')),
                ('state', models.CharField(max_length=40, verbose_name='State')),
                ('country', models.IntegerField(choices=[(581, 'United States')], default=581, verbose_name='Country')),
                ('postal_code', models.CharField(blank=True, max_length=16, verbose_name='Postal Code')),
            ],
        ),
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='last updated')),
                ('currency', models.CharField(choices=[('afn', 'AFN'), ('eur', 'EUR'), ('all', 'ALL'), ('dzd', 'DZD'), ('usd', 'USD'), ('aoa', 'AOA'), ('xcd', 'XCD'), ('ars', 'ARS'), ('amd', 'AMD'), ('awg', 'AWG'), ('aud', 'AUD'), ('azn', 'AZN'), ('bsd', 'BSD'), ('bhd', 'BHD'), ('bdt', 'BDT'), ('bbd', 'BBD'), ('byn', 'BYN'), ('bzd', 'BZD'), ('xof', 'XOF'), ('bmd', 'BMD'), ('inr', 'INR'), ('btn', 'BTN'), ('bob', 'BOB'), ('bov', 'BOV'), ('bam', 'BAM'), ('bwp', 'BWP'), ('nok', 'NOK'), ('brl', 'BRL'), ('bnd', 'BND'), ('bgn', 'BGN'), ('bif', 'BIF'), ('cve', 'CVE'), ('khr', 'KHR'), ('xaf', 'XAF'), ('cad', 'CAD'), ('kyd', 'KYD'), ('clp', 'CLP'), ('clf', 'CLF'), ('cny', 'CNY'), ('cop', 'COP'), ('cou', 'COU'), ('kmf', 'KMF'), ('cdf', 'CDF'), ('nzd', 'NZD'), ('crc', 'CRC'), ('hrk', 'HRK'), ('cup', 'CUP'), ('cuc', 'CUC'), ('ang', 'ANG'), ('czk', 'CZK'), ('dkk', 'DKK'), ('djf', 'DJF'), ('dop', 'DOP'), ('egp', 'EGP'), ('svc', 'SVC'), ('ern', 'ERN'), ('etb', 'ETB'), ('fkp', 'FKP'), ('fjd', 'FJD'), ('xpf', 'XPF'), ('gmd', 'GMD'), ('gel', 'GEL'), ('ghs', 'GHS'), ('gip', 'GIP'), ('gtq', 'GTQ'), ('gbp', 'GBP'), ('gnf', 'GNF'), ('gyd', 'GYD'), ('htg', 'HTG'), ('hnl', 'HNL'), ('hkd', 'HKD'), ('huf', 'HUF'), ('isk', 'ISK'), ('idr', 'IDR'), ('irr', 'IRR'), ('iqd', 'IQD'), ('ils', 'ILS'), ('jmd', 'JMD'), ('jpy', 'JPY'), ('jod', 'JOD'), ('kzt', 'KZT'), ('kes', 'KES'), ('kpw', 'KPW'), ('krw', 'KRW'), ('kwd', 'KWD'), ('kgs', 'KGS'), ('lak', 'LAK'), ('lbp', 'LBP'), ('lsl', 'LSL'), ('zar', 'ZAR'), ('lrd', 'LRD'), ('lyd', 'LYD'), ('chf', 'CHF'), ('mop', 'MOP'), ('mkd', 'MKD'), ('mga', 'MGA'), ('mwk', 'MWK'), ('myr', 'MYR'), ('mvr', 'MVR'), ('mru', 'MRU'), ('mur', 'MUR'), ('mxn', 'MXN'), ('mxv', 'MXV'), ('mdl', 'MDL'), ('mnt', 'MNT'), ('mad', 'MAD'), ('mzn', 'MZN'), ('mmk', 'MMK'), ('nad', 'NAD'), ('npr', 'NPR'), ('nio', 'NIO'), ('ngn', 'NGN'), ('omr', 'OMR'), ('pkr', 'PKR'), ('pab', 'PAB'), ('pgk', 'PGK'), ('pyg', 'PYG'), ('pen', 'PEN'), ('php', 'PHP'), ('pln', 'PLN'), ('qar', 'QAR'), ('ron', 'RON'), ('rub', 'RUB'), ('rwf', 'RWF'), ('shp', 'SHP'), ('wst', 'WST'), ('stn', 'STN'), ('sar', 'SAR'), ('rsd', 'RSD'), ('scr', 'SCR'), ('sll', 'SLL'), ('sgd', 'SGD'), ('sbd', 'SBD'), ('sos', 'SOS'), ('ssp', 'SSP'), ('lkr', 'LKR'), ('sdg', 'SDG'), ('srd', 'SRD'), ('szl', 'SZL'), ('sek', 'SEK'), ('che', 'CHE'), ('chw', 'CHW'), ('syp', 'SYP'), ('twd', 'TWD'), ('tjs', 'TJS'), ('tzs', 'TZS'), ('thb', 'THB'), ('top', 'TOP'), ('ttd', 'TTD'), ('tnd', 'TND'), ('try', 'TRY'), ('tmt', 'TMT'), ('ugx', 'UGX'), ('uah', 'UAH'), ('aed', 'AED'), ('usn', 'USN'), ('uyu', 'UYU'), ('uyi', 'UYI'), ('uyw', 'UYW'), ('uzs', 'UZS'), ('vuv', 'VUV'), ('ves', 'VES'), ('vnd', 'VND'), ('yer', 'YER'), ('zmw', 'ZMW'), ('zwl', 'ZWL')], default='usd', max_length=4, verbose_name='Currency')),
                ('site', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='customer_profile', to='sites.site')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_profile', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Customer Profile',
                'verbose_name_plural': 'Customer Profiles',
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('on_site', django.contrib.sites.managers.CurrentSiteManager()),
            ],
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='last updated')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID')),
                ('status', models.IntegerField(choices=[(0, 'Cart'), (10, 'Checkout'), (20, 'Queued'), (30, 'Processing'), (40, 'Failed'), (50, 'Complete'), (60, 'Refunded')], default=0, verbose_name='Status')),
                ('customer_notes', models.JSONField(blank=True, default=dict, null=True, verbose_name='Customer Notes')),
                ('vendor_notes', models.JSONField(blank=True, default=dict, null=True, verbose_name='Vendor Notes')),
                ('ordered_date', models.DateTimeField(blank=True, null=True, verbose_name='Ordered Date')),
                ('subtotal', models.FloatField(default=0.0)),
                ('tax', models.FloatField(blank=True, null=True)),
                ('shipping', models.FloatField(blank=True, null=True)),
                ('total', models.FloatField(blank=True, null=True)),
                ('currency', models.CharField(choices=[('afn', 'AFN'), ('eur', 'EUR'), ('all', 'ALL'), ('dzd', 'DZD'), ('usd', 'USD'), ('aoa', 'AOA'), ('xcd', 'XCD'), ('ars', 'ARS'), ('amd', 'AMD'), ('awg', 'AWG'), ('aud', 'AUD'), ('azn', 'AZN'), ('bsd', 'BSD'), ('bhd', 'BHD'), ('bdt', 'BDT'), ('bbd', 'BBD'), ('byn', 'BYN'), ('bzd', 'BZD'), ('xof', 'XOF'), ('bmd', 'BMD'), ('inr', 'INR'), ('btn', 'BTN'), ('bob', 'BOB'), ('bov', 'BOV'), ('bam', 'BAM'), ('bwp', 'BWP'), ('nok', 'NOK'), ('brl', 'BRL'), ('bnd', 'BND'), ('bgn', 'BGN'), ('bif', 'BIF'), ('cve', 'CVE'), ('khr', 'KHR'), ('xaf', 'XAF'), ('cad', 'CAD'), ('kyd', 'KYD'), ('clp', 'CLP'), ('clf', 'CLF'), ('cny', 'CNY'), ('cop', 'COP'), ('cou', 'COU'), ('kmf', 'KMF'), ('cdf', 'CDF'), ('nzd', 'NZD'), ('crc', 'CRC'), ('hrk', 'HRK'), ('cup', 'CUP'), ('cuc', 'CUC'), ('ang', 'ANG'), ('czk', 'CZK'), ('dkk', 'DKK'), ('djf', 'DJF'), ('dop', 'DOP'), ('egp', 'EGP'), ('svc', 'SVC'), ('ern', 'ERN'), ('etb', 'ETB'), ('fkp', 'FKP'), ('fjd', 'FJD'), ('xpf', 'XPF'), ('gmd', 'GMD'), ('gel', 'GEL'), ('ghs', 'GHS'), ('gip', 'GIP'), ('gtq', 'GTQ'), ('gbp', 'GBP'), ('gnf', 'GNF'), ('gyd', 'GYD'), ('htg', 'HTG'), ('hnl', 'HNL'), ('hkd', 'HKD'), ('huf', 'HUF'), ('isk', 'ISK'), ('idr', 'IDR'), ('irr', 'IRR'), ('iqd', 'IQD'), ('ils', 'ILS'), ('jmd', 'JMD'), ('jpy', 'JPY'), ('jod', 'JOD'), ('kzt', 'KZT'), ('kes', 'KES'), ('kpw', 'KPW'), ('krw', 'KRW'), ('kwd', 'KWD'), ('kgs', 'KGS'), ('lak', 'LAK'), ('lbp', 'LBP'), ('lsl', 'LSL'), ('zar', 'ZAR'), ('lrd', 'LRD'), ('lyd', 'LYD'), ('chf', 'CHF'), ('mop', 'MOP'), ('mkd', 'MKD'), ('mga', 'MGA'), ('mwk', 'MWK'), ('myr', 'MYR'), ('mvr', 'MVR'), ('mru', 'MRU'), ('mur', 'MUR'), ('mxn', 'MXN'), ('mxv', 'MXV'), ('mdl', 'MDL'), ('mnt', 'MNT'), ('mad', 'MAD'), ('mzn', 'MZN'), ('mmk', 'MMK'), ('nad', 'NAD'), ('npr', 'NPR'), ('nio', 'NIO'), ('ngn', 'NGN'), ('omr', 'OMR'), ('pkr', 'PKR'), ('pab', 'PAB'), ('pgk', 'PGK'), ('pyg', 'PYG'), ('pen', 'PEN'), ('php', 'PHP'), ('pln', 'PLN'), ('qar', 'QAR'), ('ron', 'RON'), ('rub', 'RUB'), ('rwf', 'RWF'), ('shp', 'SHP'), ('wst', 'WST'), ('stn', 'STN'), ('sar', 'SAR'), ('rsd', 'RSD'), ('scr', 'SCR'), ('sll', 'SLL'), ('sgd', 'SGD'), ('sbd', 'SBD'), ('sos', 'SOS'), ('ssp', 'SSP'), ('lkr', 'LKR'), ('sdg', 'SDG'), ('srd', 'SRD'), ('szl', 'SZL'), ('sek', 'SEK'), ('che', 'CHE'), ('chw', 'CHW'), ('syp', 'SYP'), ('twd', 'TWD'), ('tjs', 'TJS'), ('tzs', 'TZS'), ('thb', 'THB'), ('top', 'TOP'), ('ttd', 'TTD'), ('tnd', 'TND'), ('try', 'TRY'), ('tmt', 'TMT'), ('ugx', 'UGX'), ('uah', 'UAH'), ('aed', 'AED'), ('usn', 'USN'), ('uyu', 'UYU'), ('uyi', 'UYI'), ('uyw', 'UYW'), ('uzs', 'UZS'), ('vuv', 'VUV'), ('ves', 'VES'), ('vnd', 'VND'), ('yer', 'YER'), ('zmw', 'ZMW'), ('zwl', 'ZWL')], default='usd', max_length=4, verbose_name='Currency')),
                ('profile', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='vendor.customerprofile', verbose_name='Customer Profile')),
                ('shipping_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vendor.address', verbose_name='Shipping Address')),
                ('site', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='sites.site')),
            ],
            options={
                'verbose_name': 'Invoice',
                'verbose_name_plural': 'Invoices',
                'ordering': ['-ordered_date', '-updated'],
                'permissions': (('can_view_site_purchases', 'Can view Site Purchases'), ('can_refund_purchase', 'Can refund Purchase')),
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('on_site', django.contrib.sites.managers.CurrentSiteManager()),
            ],
        ),
        migrations.CreateModel(
            name='Offer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='last updated')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=False, populate_from='name', unique_with=('site__id',))),
                ('name', models.CharField(blank=True, max_length=80, verbose_name='Name')),
                ('start_date', models.DateTimeField(help_text='What date should this offer become available?', verbose_name='Start Date')),
                ('end_date', models.DateTimeField(blank=True, help_text='Expiration Date?', null=True, verbose_name='End Date')),
                ('terms', models.IntegerField(choices=[(0, 'Perpetual'), (10, 'Subscription'), (20, 'One-Time Use')], default=0, verbose_name='Terms')),
                ('term_details', models.JSONField(blank=True, default=dict, null=True, verbose_name='Term Details')),
                ('term_start_date', models.DateTimeField(blank=True, help_text='When is this product available to use?', null=True, verbose_name='Term Start Date')),
                ('available', models.BooleanField(default=False, help_text='Is this currently available?', verbose_name='Available')),
                ('bundle', models.BooleanField(default=False, help_text='Is this a product bundle? (auto-generated)', verbose_name='Is a Bundle?')),
                ('site', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='product_offers', to='sites.site')),
            ],
            options={
                'verbose_name': 'Offer',
                'verbose_name_plural': 'Offers',
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('on_site', django.contrib.sites.managers.CurrentSiteManager()),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='last updated')),
                ('quantity', models.IntegerField(default=1, verbose_name='Quantity')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='vendor.invoice', verbose_name='Invoice')),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='vendor.offer', verbose_name='Offer')),
            ],
            options={
                'verbose_name': 'Order Item',
                'verbose_name_plural': 'Order Items',
            },
        ),
        migrations.CreateModel(
            name='TaxClassifier',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=80, verbose_name='Name')),
                ('taxable', models.BooleanField()),
            ],
            options={
                'verbose_name': 'Product Classifier',
                'verbose_name_plural': 'Product Classifiers',
            },
        ),
        migrations.CreateModel(
            name='Wishlist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('profile', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='wishlists', to='vendor.customerprofile', verbose_name='Purchase Profile')),
            ],
            options={
                'verbose_name': 'Wishlist',
                'verbose_name_plural': 'Wishlists',
            },
        ),
        migrations.CreateModel(
            name='WishlistItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='last updated')),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wishlist_items', to='vendor.offer', verbose_name='Offer')),
                ('wishlist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wishlist_items', to='vendor.wishlist', verbose_name='Wishlist')),
            ],
            options={
                'verbose_name': 'Wishlist Item',
                'verbose_name_plural': 'Wishlist Items',
            },
        ),
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='last updated')),
                ('start_date', models.DateTimeField(blank=True, null=True, verbose_name='Start Date')),
                ('end_date', models.DateTimeField(blank=True, null=True, verbose_name='End Date')),
                ('auto_renew', models.BooleanField(default=False, verbose_name='Auto Renew')),
                ('vendor_notes', models.JSONField(default=dict, verbose_name='Vendor Notes')),
                ('transaction', models.CharField(max_length=80, verbose_name='Transaction')),
                ('status', models.IntegerField(choices=[(1, 'Queued'), (2, 'Active'), (10, 'Authorized'), (15, 'Captured'), (20, 'Completed'), (30, 'Canceled'), (35, 'Refunded')], default=0, verbose_name='Status')),
                ('meta', models.JSONField(default=dict)),
                ('order_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='vendor.orderitem', verbose_name='Order Item')),
                ('profile', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='vendor.customerprofile', verbose_name='Purchase Profile')),
            ],
            options={
                'verbose_name': 'Receipt',
                'verbose_name_plural': 'Receipts',
            },
        ),
        migrations.CreateModel(
            name='Price',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost', models.FloatField(blank=True, null=True)),
                ('currency', models.CharField(choices=[('afn', 'AFN'), ('eur', 'EUR'), ('all', 'ALL'), ('dzd', 'DZD'), ('usd', 'USD'), ('aoa', 'AOA'), ('xcd', 'XCD'), ('ars', 'ARS'), ('amd', 'AMD'), ('awg', 'AWG'), ('aud', 'AUD'), ('azn', 'AZN'), ('bsd', 'BSD'), ('bhd', 'BHD'), ('bdt', 'BDT'), ('bbd', 'BBD'), ('byn', 'BYN'), ('bzd', 'BZD'), ('xof', 'XOF'), ('bmd', 'BMD'), ('inr', 'INR'), ('btn', 'BTN'), ('bob', 'BOB'), ('bov', 'BOV'), ('bam', 'BAM'), ('bwp', 'BWP'), ('nok', 'NOK'), ('brl', 'BRL'), ('bnd', 'BND'), ('bgn', 'BGN'), ('bif', 'BIF'), ('cve', 'CVE'), ('khr', 'KHR'), ('xaf', 'XAF'), ('cad', 'CAD'), ('kyd', 'KYD'), ('clp', 'CLP'), ('clf', 'CLF'), ('cny', 'CNY'), ('cop', 'COP'), ('cou', 'COU'), ('kmf', 'KMF'), ('cdf', 'CDF'), ('nzd', 'NZD'), ('crc', 'CRC'), ('hrk', 'HRK'), ('cup', 'CUP'), ('cuc', 'CUC'), ('ang', 'ANG'), ('czk', 'CZK'), ('dkk', 'DKK'), ('djf', 'DJF'), ('dop', 'DOP'), ('egp', 'EGP'), ('svc', 'SVC'), ('ern', 'ERN'), ('etb', 'ETB'), ('fkp', 'FKP'), ('fjd', 'FJD'), ('xpf', 'XPF'), ('gmd', 'GMD'), ('gel', 'GEL'), ('ghs', 'GHS'), ('gip', 'GIP'), ('gtq', 'GTQ'), ('gbp', 'GBP'), ('gnf', 'GNF'), ('gyd', 'GYD'), ('htg', 'HTG'), ('hnl', 'HNL'), ('hkd', 'HKD'), ('huf', 'HUF'), ('isk', 'ISK'), ('idr', 'IDR'), ('irr', 'IRR'), ('iqd', 'IQD'), ('ils', 'ILS'), ('jmd', 'JMD'), ('jpy', 'JPY'), ('jod', 'JOD'), ('kzt', 'KZT'), ('kes', 'KES'), ('kpw', 'KPW'), ('krw', 'KRW'), ('kwd', 'KWD'), ('kgs', 'KGS'), ('lak', 'LAK'), ('lbp', 'LBP'), ('lsl', 'LSL'), ('zar', 'ZAR'), ('lrd', 'LRD'), ('lyd', 'LYD'), ('chf', 'CHF'), ('mop', 'MOP'), ('mkd', 'MKD'), ('mga', 'MGA'), ('mwk', 'MWK'), ('myr', 'MYR'), ('mvr', 'MVR'), ('mru', 'MRU'), ('mur', 'MUR'), ('mxn', 'MXN'), ('mxv', 'MXV'), ('mdl', 'MDL'), ('mnt', 'MNT'), ('mad', 'MAD'), ('mzn', 'MZN'), ('mmk', 'MMK'), ('nad', 'NAD'), ('npr', 'NPR'), ('nio', 'NIO'), ('ngn', 'NGN'), ('omr', 'OMR'), ('pkr', 'PKR'), ('pab', 'PAB'), ('pgk', 'PGK'), ('pyg', 'PYG'), ('pen', 'PEN'), ('php', 'PHP'), ('pln', 'PLN'), ('qar', 'QAR'), ('ron', 'RON'), ('rub', 'RUB'), ('rwf', 'RWF'), ('shp', 'SHP'), ('wst', 'WST'), ('stn', 'STN'), ('sar', 'SAR'), ('rsd', 'RSD'), ('scr', 'SCR'), ('sll', 'SLL'), ('sgd', 'SGD'), ('sbd', 'SBD'), ('sos', 'SOS'), ('ssp', 'SSP'), ('lkr', 'LKR'), ('sdg', 'SDG'), ('srd', 'SRD'), ('szl', 'SZL'), ('sek', 'SEK'), ('che', 'CHE'), ('chw', 'CHW'), ('syp', 'SYP'), ('twd', 'TWD'), ('tjs', 'TJS'), ('tzs', 'TZS'), ('thb', 'THB'), ('top', 'TOP'), ('ttd', 'TTD'), ('tnd', 'TND'), ('try', 'TRY'), ('tmt', 'TMT'), ('ugx', 'UGX'), ('uah', 'UAH'), ('aed', 'AED'), ('usn', 'USN'), ('uyu', 'UYU'), ('uyi', 'UYI'), ('uyw', 'UYW'), ('uzs', 'UZS'), ('vuv', 'VUV'), ('ves', 'VES'), ('vnd', 'VND'), ('yer', 'YER'), ('zmw', 'ZMW'), ('zwl', 'ZWL')], default='usd', max_length=4, verbose_name='Currency')),
                ('start_date', models.DateTimeField(help_text='When should the price first become available?', verbose_name='Start Date')),
                ('end_date', models.DateTimeField(blank=True, help_text='When should the price expire?', null=True, verbose_name='End Date')),
                ('priority', models.IntegerField(blank=True, help_text='Higher number takes priority', null=True, verbose_name='Priority')),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='vendor.offer')),
            ],
            options={
                'verbose_name': 'Price',
                'verbose_name_plural': 'Prices',
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('transaction', models.CharField(max_length=50, verbose_name='Transaction ID')),
                ('provider', models.CharField(max_length=30, verbose_name='Payment Provider')),
                ('amount', models.FloatField(verbose_name='Amount')),
                ('result', models.JSONField(blank=True, default=dict, null=True, verbose_name='Result')),
                ('success', models.BooleanField(default=False, verbose_name='Successful')),
                ('payee_full_name', models.CharField(max_length=50, verbose_name='Name on Card')),
                ('payee_company', models.CharField(blank=True, max_length=50, null=True, verbose_name='Company')),
                ('billing_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vendor.address', verbose_name='payments')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='vendor.invoice', verbose_name='Invoice')),
                ('profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='vendor.customerprofile', verbose_name='Purchase Profile')),
            ],
        ),
        migrations.AddField(
            model_name='address',
            name='profile',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to='vendor.customerprofile', verbose_name='Customer Profile'),
        ),
    ]
