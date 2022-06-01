# Generated by Django 3.2.13 on 2022-04-14 10:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0029_alter_customerprofile_currency_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerprofile',
            name='currency',
            field=models.CharField(choices=[('afn', 'AFN'), ('eur', 'EUR'), ('all', 'ALL'), ('dzd', 'DZD'), ('usd', 'USD'), ('aoa', 'AOA'), ('xcd', 'XCD'), ('ars', 'ARS'), ('amd', 'AMD'), ('awg', 'AWG'), ('aud', 'AUD'), ('azn', 'AZN'), ('bsd', 'BSD'), ('bhd', 'BHD'), ('bdt', 'BDT'), ('bbd', 'BBD'), ('byn', 'BYN'), ('bzd', 'BZD'), ('xof', 'XOF'), ('bmd', 'BMD'), ('inr', 'INR'), ('btn', 'BTN'), ('bob', 'BOB'), ('bov', 'BOV'), ('bam', 'BAM'), ('bwp', 'BWP'), ('nok', 'NOK'), ('brl', 'BRL'), ('bnd', 'BND'), ('bgn', 'BGN'), ('bif', 'BIF'), ('cve', 'CVE'), ('khr', 'KHR'), ('xaf', 'XAF'), ('cad', 'CAD'), ('kyd', 'KYD'), ('clp', 'CLP'), ('clf', 'CLF'), ('cny', 'CNY'), ('cop', 'COP'), ('cou', 'COU'), ('kmf', 'KMF'), ('cdf', 'CDF'), ('nzd', 'NZD'), ('crc', 'CRC'), ('hrk', 'HRK'), ('cup', 'CUP'), ('cuc', 'CUC'), ('ang', 'ANG'), ('czk', 'CZK'), ('dkk', 'DKK'), ('djf', 'DJF'), ('dop', 'DOP'), ('egp', 'EGP'), ('svc', 'SVC'), ('ern', 'ERN'), ('szl', 'SZL'), ('etb', 'ETB'), ('fkp', 'FKP'), ('fjd', 'FJD'), ('xpf', 'XPF'), ('gmd', 'GMD'), ('gel', 'GEL'), ('ghs', 'GHS'), ('gip', 'GIP'), ('gtq', 'GTQ'), ('gbp', 'GBP'), ('gnf', 'GNF'), ('gyd', 'GYD'), ('htg', 'HTG'), ('hnl', 'HNL'), ('hkd', 'HKD'), ('huf', 'HUF'), ('isk', 'ISK'), ('idr', 'IDR'), ('xdr', 'XDR'), ('irr', 'IRR'), ('iqd', 'IQD'), ('ils', 'ILS'), ('jmd', 'JMD'), ('jpy', 'JPY'), ('jod', 'JOD'), ('kzt', 'KZT'), ('kes', 'KES'), ('kpw', 'KPW'), ('krw', 'KRW'), ('kwd', 'KWD'), ('kgs', 'KGS'), ('lak', 'LAK'), ('lbp', 'LBP'), ('lsl', 'LSL'), ('zar', 'ZAR'), ('lrd', 'LRD'), ('lyd', 'LYD'), ('chf', 'CHF'), ('mop', 'MOP'), ('mkd', 'MKD'), ('mga', 'MGA'), ('mwk', 'MWK'), ('myr', 'MYR'), ('mvr', 'MVR'), ('mru', 'MRU'), ('mur', 'MUR'), ('xua', 'XUA'), ('mxn', 'MXN'), ('mxv', 'MXV'), ('mdl', 'MDL'), ('mnt', 'MNT'), ('mad', 'MAD'), ('mzn', 'MZN'), ('mmk', 'MMK'), ('nad', 'NAD'), ('npr', 'NPR'), ('nio', 'NIO'), ('ngn', 'NGN'), ('omr', 'OMR'), ('pkr', 'PKR'), ('pab', 'PAB'), ('pgk', 'PGK'), ('pyg', 'PYG'), ('pen', 'PEN'), ('php', 'PHP'), ('pln', 'PLN'), ('qar', 'QAR'), ('ron', 'RON'), ('rub', 'RUB'), ('rwf', 'RWF'), ('shp', 'SHP'), ('wst', 'WST'), ('stn', 'STN'), ('sar', 'SAR'), ('rsd', 'RSD'), ('scr', 'SCR'), ('sll', 'SLL'), ('sle', 'SLE'), ('sgd', 'SGD'), ('xsu', 'XSU'), ('sbd', 'SBD'), ('sos', 'SOS'), ('ssp', 'SSP'), ('lkr', 'LKR'), ('sdg', 'SDG'), ('srd', 'SRD'), ('sek', 'SEK'), ('che', 'CHE'), ('chw', 'CHW'), ('syp', 'SYP'), ('twd', 'TWD'), ('tjs', 'TJS'), ('tzs', 'TZS'), ('thb', 'THB'), ('top', 'TOP'), ('ttd', 'TTD'), ('tnd', 'TND'), ('try', 'TRY'), ('tmt', 'TMT'), ('ugx', 'UGX'), ('uah', 'UAH'), ('aed', 'AED'), ('usn', 'USN'), ('uyu', 'UYU'), ('uyi', 'UYI'), ('uyw', 'UYW'), ('uzs', 'UZS'), ('vuv', 'VUV'), ('ves', 'VES'), ('ved', 'VED'), ('vnd', 'VND'), ('yer', 'YER'), ('zmw', 'ZMW'), ('zwl', 'ZWL'), ('xba', 'XBA'), ('xbb', 'XBB'), ('xbc', 'XBC'), ('xbd', 'XBD'), ('xts', 'XTS'), ('xxx', 'XXX'), ('xau', 'XAU'), ('xpd', 'XPD'), ('xpt', 'XPT'), ('xag', 'XAG')], default='usd', max_length=4, verbose_name='Currency'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='currency',
            field=models.CharField(choices=[('afn', 'AFN'), ('eur', 'EUR'), ('all', 'ALL'), ('dzd', 'DZD'), ('usd', 'USD'), ('aoa', 'AOA'), ('xcd', 'XCD'), ('ars', 'ARS'), ('amd', 'AMD'), ('awg', 'AWG'), ('aud', 'AUD'), ('azn', 'AZN'), ('bsd', 'BSD'), ('bhd', 'BHD'), ('bdt', 'BDT'), ('bbd', 'BBD'), ('byn', 'BYN'), ('bzd', 'BZD'), ('xof', 'XOF'), ('bmd', 'BMD'), ('inr', 'INR'), ('btn', 'BTN'), ('bob', 'BOB'), ('bov', 'BOV'), ('bam', 'BAM'), ('bwp', 'BWP'), ('nok', 'NOK'), ('brl', 'BRL'), ('bnd', 'BND'), ('bgn', 'BGN'), ('bif', 'BIF'), ('cve', 'CVE'), ('khr', 'KHR'), ('xaf', 'XAF'), ('cad', 'CAD'), ('kyd', 'KYD'), ('clp', 'CLP'), ('clf', 'CLF'), ('cny', 'CNY'), ('cop', 'COP'), ('cou', 'COU'), ('kmf', 'KMF'), ('cdf', 'CDF'), ('nzd', 'NZD'), ('crc', 'CRC'), ('hrk', 'HRK'), ('cup', 'CUP'), ('cuc', 'CUC'), ('ang', 'ANG'), ('czk', 'CZK'), ('dkk', 'DKK'), ('djf', 'DJF'), ('dop', 'DOP'), ('egp', 'EGP'), ('svc', 'SVC'), ('ern', 'ERN'), ('szl', 'SZL'), ('etb', 'ETB'), ('fkp', 'FKP'), ('fjd', 'FJD'), ('xpf', 'XPF'), ('gmd', 'GMD'), ('gel', 'GEL'), ('ghs', 'GHS'), ('gip', 'GIP'), ('gtq', 'GTQ'), ('gbp', 'GBP'), ('gnf', 'GNF'), ('gyd', 'GYD'), ('htg', 'HTG'), ('hnl', 'HNL'), ('hkd', 'HKD'), ('huf', 'HUF'), ('isk', 'ISK'), ('idr', 'IDR'), ('xdr', 'XDR'), ('irr', 'IRR'), ('iqd', 'IQD'), ('ils', 'ILS'), ('jmd', 'JMD'), ('jpy', 'JPY'), ('jod', 'JOD'), ('kzt', 'KZT'), ('kes', 'KES'), ('kpw', 'KPW'), ('krw', 'KRW'), ('kwd', 'KWD'), ('kgs', 'KGS'), ('lak', 'LAK'), ('lbp', 'LBP'), ('lsl', 'LSL'), ('zar', 'ZAR'), ('lrd', 'LRD'), ('lyd', 'LYD'), ('chf', 'CHF'), ('mop', 'MOP'), ('mkd', 'MKD'), ('mga', 'MGA'), ('mwk', 'MWK'), ('myr', 'MYR'), ('mvr', 'MVR'), ('mru', 'MRU'), ('mur', 'MUR'), ('xua', 'XUA'), ('mxn', 'MXN'), ('mxv', 'MXV'), ('mdl', 'MDL'), ('mnt', 'MNT'), ('mad', 'MAD'), ('mzn', 'MZN'), ('mmk', 'MMK'), ('nad', 'NAD'), ('npr', 'NPR'), ('nio', 'NIO'), ('ngn', 'NGN'), ('omr', 'OMR'), ('pkr', 'PKR'), ('pab', 'PAB'), ('pgk', 'PGK'), ('pyg', 'PYG'), ('pen', 'PEN'), ('php', 'PHP'), ('pln', 'PLN'), ('qar', 'QAR'), ('ron', 'RON'), ('rub', 'RUB'), ('rwf', 'RWF'), ('shp', 'SHP'), ('wst', 'WST'), ('stn', 'STN'), ('sar', 'SAR'), ('rsd', 'RSD'), ('scr', 'SCR'), ('sll', 'SLL'), ('sle', 'SLE'), ('sgd', 'SGD'), ('xsu', 'XSU'), ('sbd', 'SBD'), ('sos', 'SOS'), ('ssp', 'SSP'), ('lkr', 'LKR'), ('sdg', 'SDG'), ('srd', 'SRD'), ('sek', 'SEK'), ('che', 'CHE'), ('chw', 'CHW'), ('syp', 'SYP'), ('twd', 'TWD'), ('tjs', 'TJS'), ('tzs', 'TZS'), ('thb', 'THB'), ('top', 'TOP'), ('ttd', 'TTD'), ('tnd', 'TND'), ('try', 'TRY'), ('tmt', 'TMT'), ('ugx', 'UGX'), ('uah', 'UAH'), ('aed', 'AED'), ('usn', 'USN'), ('uyu', 'UYU'), ('uyi', 'UYI'), ('uyw', 'UYW'), ('uzs', 'UZS'), ('vuv', 'VUV'), ('ves', 'VES'), ('ved', 'VED'), ('vnd', 'VND'), ('yer', 'YER'), ('zmw', 'ZMW'), ('zwl', 'ZWL'), ('xba', 'XBA'), ('xbb', 'XBB'), ('xbc', 'XBC'), ('xbd', 'XBD'), ('xts', 'XTS'), ('xxx', 'XXX'), ('xau', 'XAU'), ('xpd', 'XPD'), ('xpt', 'XPT'), ('xag', 'XAG')], default='usd', max_length=4, verbose_name='Currency'),
        ),
        migrations.AlterField(
            model_name='price',
            name='currency',
            field=models.CharField(choices=[('afn', 'AFN'), ('eur', 'EUR'), ('all', 'ALL'), ('dzd', 'DZD'), ('usd', 'USD'), ('aoa', 'AOA'), ('xcd', 'XCD'), ('ars', 'ARS'), ('amd', 'AMD'), ('awg', 'AWG'), ('aud', 'AUD'), ('azn', 'AZN'), ('bsd', 'BSD'), ('bhd', 'BHD'), ('bdt', 'BDT'), ('bbd', 'BBD'), ('byn', 'BYN'), ('bzd', 'BZD'), ('xof', 'XOF'), ('bmd', 'BMD'), ('inr', 'INR'), ('btn', 'BTN'), ('bob', 'BOB'), ('bov', 'BOV'), ('bam', 'BAM'), ('bwp', 'BWP'), ('nok', 'NOK'), ('brl', 'BRL'), ('bnd', 'BND'), ('bgn', 'BGN'), ('bif', 'BIF'), ('cve', 'CVE'), ('khr', 'KHR'), ('xaf', 'XAF'), ('cad', 'CAD'), ('kyd', 'KYD'), ('clp', 'CLP'), ('clf', 'CLF'), ('cny', 'CNY'), ('cop', 'COP'), ('cou', 'COU'), ('kmf', 'KMF'), ('cdf', 'CDF'), ('nzd', 'NZD'), ('crc', 'CRC'), ('hrk', 'HRK'), ('cup', 'CUP'), ('cuc', 'CUC'), ('ang', 'ANG'), ('czk', 'CZK'), ('dkk', 'DKK'), ('djf', 'DJF'), ('dop', 'DOP'), ('egp', 'EGP'), ('svc', 'SVC'), ('ern', 'ERN'), ('szl', 'SZL'), ('etb', 'ETB'), ('fkp', 'FKP'), ('fjd', 'FJD'), ('xpf', 'XPF'), ('gmd', 'GMD'), ('gel', 'GEL'), ('ghs', 'GHS'), ('gip', 'GIP'), ('gtq', 'GTQ'), ('gbp', 'GBP'), ('gnf', 'GNF'), ('gyd', 'GYD'), ('htg', 'HTG'), ('hnl', 'HNL'), ('hkd', 'HKD'), ('huf', 'HUF'), ('isk', 'ISK'), ('idr', 'IDR'), ('xdr', 'XDR'), ('irr', 'IRR'), ('iqd', 'IQD'), ('ils', 'ILS'), ('jmd', 'JMD'), ('jpy', 'JPY'), ('jod', 'JOD'), ('kzt', 'KZT'), ('kes', 'KES'), ('kpw', 'KPW'), ('krw', 'KRW'), ('kwd', 'KWD'), ('kgs', 'KGS'), ('lak', 'LAK'), ('lbp', 'LBP'), ('lsl', 'LSL'), ('zar', 'ZAR'), ('lrd', 'LRD'), ('lyd', 'LYD'), ('chf', 'CHF'), ('mop', 'MOP'), ('mkd', 'MKD'), ('mga', 'MGA'), ('mwk', 'MWK'), ('myr', 'MYR'), ('mvr', 'MVR'), ('mru', 'MRU'), ('mur', 'MUR'), ('xua', 'XUA'), ('mxn', 'MXN'), ('mxv', 'MXV'), ('mdl', 'MDL'), ('mnt', 'MNT'), ('mad', 'MAD'), ('mzn', 'MZN'), ('mmk', 'MMK'), ('nad', 'NAD'), ('npr', 'NPR'), ('nio', 'NIO'), ('ngn', 'NGN'), ('omr', 'OMR'), ('pkr', 'PKR'), ('pab', 'PAB'), ('pgk', 'PGK'), ('pyg', 'PYG'), ('pen', 'PEN'), ('php', 'PHP'), ('pln', 'PLN'), ('qar', 'QAR'), ('ron', 'RON'), ('rub', 'RUB'), ('rwf', 'RWF'), ('shp', 'SHP'), ('wst', 'WST'), ('stn', 'STN'), ('sar', 'SAR'), ('rsd', 'RSD'), ('scr', 'SCR'), ('sll', 'SLL'), ('sle', 'SLE'), ('sgd', 'SGD'), ('xsu', 'XSU'), ('sbd', 'SBD'), ('sos', 'SOS'), ('ssp', 'SSP'), ('lkr', 'LKR'), ('sdg', 'SDG'), ('srd', 'SRD'), ('sek', 'SEK'), ('che', 'CHE'), ('chw', 'CHW'), ('syp', 'SYP'), ('twd', 'TWD'), ('tjs', 'TJS'), ('tzs', 'TZS'), ('thb', 'THB'), ('top', 'TOP'), ('ttd', 'TTD'), ('tnd', 'TND'), ('try', 'TRY'), ('tmt', 'TMT'), ('ugx', 'UGX'), ('uah', 'UAH'), ('aed', 'AED'), ('usn', 'USN'), ('uyu', 'UYU'), ('uyi', 'UYI'), ('uyw', 'UYW'), ('uzs', 'UZS'), ('vuv', 'VUV'), ('ves', 'VES'), ('ved', 'VED'), ('vnd', 'VND'), ('yer', 'YER'), ('zmw', 'ZMW'), ('zwl', 'ZWL'), ('xba', 'XBA'), ('xbb', 'XBB'), ('xbc', 'XBC'), ('xbd', 'XBD'), ('xts', 'XTS'), ('xxx', 'XXX'), ('xau', 'XAU'), ('xpd', 'XPD'), ('xpt', 'XPT'), ('xag', 'XAG')], default='usd', max_length=4, verbose_name='Currency'),
        ),
    ]