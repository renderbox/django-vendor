from django.utils.translation import gettext_lazy as _
from django.db import models

from iso4217 import Currency

###########
# CHOICES
###########

CURRENCY_CHOICES = [(c.name, c.value) for c in Currency]


class InvoiceStatus(models.IntegerChoices):
    CART = 0, _("Cart")               # total = subtotal = sum(OrderItems.Offer.Price + Product.TaxClassifier). Avalara
    CHECKOUT = 10, _("Checkout")      # total = subtotal + shipping + Tax against Addrr if any.
    COMPLETE = 20, _("Complete")      # Payment Processor Completed Transaction.


class TermType(models.IntegerChoices):
    SUBSCRIPTION = 100, _("Subscription")
    MONTHLY_SUBSCRIPTION = 101, _("Monthly Subscription")
    QUARTERLY_SUBSCRIPTION = 103, _("Quarterly Subscription")
    SEMIANNUAL_SUBSCRIPTION = 106, _("Semi-Annual Subscription")
    ANNUAL_SUBSCRIPTION = 112, _("Annual Subscription")
    PERPETUAL = 200, _("Perpetual")
    ONE_TIME_USE = 220, _("One-Time Use")


class PurchaseStatus(models.IntegerChoices):
    QUEUED = 1, _("Queued")
    ACTIVE = 2, _("Active")
    AUTHORIZED = 10, _("Authorized")
    CAPTURED = 15, _("Captured")
    SETTLED = 20, _("Settled")
    CANCELED = 30, _("Canceled")
    REFUNDED = 35, _("Refunded")
    DECLINED = 40, _("Declined")
    VOID = 50, _('Void')

class SubscriptionStatus(models.IntegerChoices):
    PAUSED = 10, _('Pause')
    ACTIVE = 20, _('Active')
    CANCELED = 30, _('Canceled')
    SUSPENDED = 40, _('Suspended')


class PaymentTypes(models.IntegerChoices):
    CREDIT_CARD = 10, _('Credit Card')
    BANK_ACCOUNT = 20, _('Bank Account')
    PAY_PAL = 30, _('Pay Pal')
    MOBILE = 40, _('Mobile')


class TransactionTypes(models.IntegerChoices):
    AUTHORIZE = 10, _('Authorize')
    CAPTURE = 20, _('Capture')
    SETTLE = 30, _('Settle')
    VOID = 40, _('Void')
    REFUND = 50, _('Refund')


class TermDetailUnits(models.IntegerChoices):
    DAY = 10, _("Day")
    MONTH = 20, _("Month")


class Country(models.IntegerChoices):
    """
    Following ISO 3166
    https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes
    """
    AD = 20, _("Andorra")
    AE = 784, _("United Arab Emirates")
    AF = 4, _("Afghanistan")
    AG = 28, _("Antigua And Barbuda")
    AI = 660, _("Anguilla")
    AL = 8, _("Albania")
    AM = 51, _("Armenia")
    AN = 530, _("Netherlands Antilles")
    AO = 24, _("Angola")
    AQ = 10, _("Antarctica")
    AR = 32, _("Argentina")
    AS = 16, _("American Samoa")
    AT = 40, _("Austria")
    AU = 36, _("Australia")
    AW = 533, _("Aruba")
    AZ = 31, _("Azerbaijan")
    BA = 70, _("Bosnia And Herzegowina")
    BB = 52, _("Barbados")
    BD = 50, _("Bangladesh")
    BE = 56, _("Belgium")
    BF = 854, _("Burkina Faso")
    BG = 100, _("Bulgaria")
    BH = 48, _("Bahrain")
    BI = 108, _("Burundi")
    BJ = 204, _("Benin")
    BM = 60, _("Bermuda")
    BN = 96, _("Brunei Darussalam")
    BO = 68, _("Bolivia")
    BR = 76, _("Brazil")
    BS = 44, _("Bahamas")
    BT = 64, _("Bhutan")
    BV = 74, _("Bouvet Island")
    BW = 72, _("Botswana")
    BY = 112, _("Belarus")
    BZ = 84, _("Belize")
    CA = 124, _("Canada")
    CC = 166, _("Cocos (Keeling) Islands")
    CD = 180, _("The Democratic Republic Of The Congo")
    CF = 140, _("Central African Republic")
    CG = 178, _("Congo")
    CH = 756, _("Switzerland")
    CI = 384, _("Cote D'ivoire")
    CK = 184, _("Cook Islands")
    CL = 152, _("Chile")
    CM = 120, _("Cameroon")
    CN = 156, _("China")
    CO = 170, _("Colombia")
    CR = 188, _("Costa Rica")
    CU = 192, _("Cuba")
    CV = 132, _("Cape Verde")
    CX = 162, _("Christmas Island")
    CY = 196, _("Cyprus")
    CZ = 203, _("Czech Republic")
    DE = 276, _("Germany")
    DJ = 262, _("Djibouti")
    DK = 208, _("Denmark")
    DM = 212, _("Dominica")
    DO = 214, _("Dominican Republic")
    DZ = 12, _("Algeria")
    EC = 218, _("Ecuador")
    EE = 233, _("Estonia")
    EG = 818, _("Egypt")
    EH = 732, _("Western Sahara")
    ER = 232, _("Eritrea")
    ES = 724, _("Spain")
    ET = 231, _("Ethiopia")
    FI = 246, _("Finland")
    FJ = 242, _("Fiji")
    FK = 238, _("Falkland Islands (Malvinas)")
    FM = 583, _("Federated States Of Micronesia")
    FO = 234, _("Faroe Islands")
    FR = 250, _("France")
    FX = 249, _("France, Metropolitan")
    GA = 266, _("Gabon")
    GB = 826, _("United Kingdom")
    GD = 308, _("Grenada")
    GE = 268, _("Georgia")
    GF = 254, _("French Guiana")
    GH = 288, _("Ghana")
    GI = 292, _("Gibraltar")
    GL = 304, _("Greenland")
    GM = 270, _("Gambia")
    GN = 324, _("Guinea")
    GP = 312, _("Guadeloupe")
    GQ = 226, _("Equatorial Guinea")
    GR = 300, _("Greece")
    GS = 239, _("South Georgia And The South Sandwich Islands")
    GT = 320, _("Guatemala")
    GU = 316, _("Guam")
    GW = 624, _("Guinea-bissau")
    GY = 328, _("Guyana")
    HK = 344, _("Hong Kong")
    HM = 334, _("Heard And Mc Donald Islands")
    HN = 340, _("Honduras")
    HR = 191, _("Croatia (Local Name: Hrvatska)")
    HT = 332, _("Haiti")
    HU = 348, _("Hungary")
    ID = 360, _("Indonesia")
    IE = 372, _("Ireland")
    IL = 376, _("Israel")
    IN = 356, _("India")
    IO = 86, _("British Indian Ocean Territory")
    IQ = 368, _("Iraq")
    IR = 364, _("Iran (Islamic Republic Of Iran)")
    IS = 352, _("Iceland")
    IT = 380, _("Italy")
    JM = 388, _("Jamaica")
    JO = 400, _("Jordan")
    JP = 392, _("Japan")
    KE = 404, _("Kenya")
    KG = 417, _("Kyrgyzstan")
    KH = 116, _("Cambodia")
    KI = 296, _("Kiribati")
    KM = 174, _("Comoros")
    KN = 659, _("Saint Kitts And Nevis")
    KP = 408, _("Democratic People's Republic Of Korea")
    KR = 410, _("Republic Of Korea")
    KW = 414, _("Kuwait")
    KY = 136, _("Cayman Islands")
    KZ = 398, _("Kazakhstan")
    LA = 418, _("Lao People's Democratic Republic")
    LB = 422, _("Lebanon")
    LC = 662, _("Saint Lucia")
    LI = 438, _("Liechtenstein")
    LK = 144, _("Sri Lanka")
    LR = 430, _("Liberia")
    LS = 426, _("Lesotho")
    LT = 440, _("Lithuania")
    LU = 442, _("Luxembourg")
    LV = 428, _("Latvia")
    LY = 434, _("Libyan Arab Jamahiriya")
    MA = 504, _("Morocco")
    MC = 492, _("Monaco")
    MD = 498, _("Republic Of Moldova")
    MG = 450, _("Madagascar")
    MH = 584, _("Marshall Islands")
    MK = 807, _("The Former Yugoslav Republic Of Macedonia ")
    ML = 466, _("Mali")
    MM = 104, _("Myanmar")
    MN = 496, _("Mongolia")
    MO = 446, _("Macau")
    MP = 580, _("Northern Mariana Islands")
    MQ = 474, _("Martinique")
    MR = 478, _("Mauritania")
    MS = 500, _("Montserrat")
    MT = 470, _("Malta")
    MU = 480, _("Mauritius")
    MV = 462, _("Maldives")
    MW = 454, _("Malawi")
    MX = 484, _("Mexico")
    MY = 458, _("Malaysia")
    MZ = 508, _("Mozambique")
    NA = 516, _("Namibia")
    NC = 540, _("New Caledonia")
    NE = 562, _("Niger")
    NF = 574, _("Norfolk Island")
    NG = 566, _("Nigeria")
    NI = 558, _("Nicaragua")
    NL = 528, _("Netherlands")
    NO = 578, _("Norway")
    NP = 524, _("Nepal")
    NR = 520, _("Nauru")
    NU = 570, _("Niue")
    NZ = 554, _("New Zealand")
    OM = 512, _("Oman")
    PA = 591, _("Panama")
    PE = 604, _("Peru")
    PF = 258, _("French Polynesia")
    PG = 598, _("Papua New Guinea")
    PH = 608, _("Philippines")
    PK = 586, _("Pakistan")
    PL = 616, _("Poland")
    PM = 666, _("St. Pierre And Miquelon")
    PN = 612, _("Pitcairn")
    PR = 630, _("Puerto Rico")
    PT = 620, _("Portugal")
    PW = 585, _("Palau")
    PY = 600, _("Paraguay")
    QA = 634, _("Qatar")
    RE = 638, _("Reunion")
    RO = 642, _("Romania")
    RU = 643, _("Russian Federation")
    RW = 646, _("Rwanda")
    SA = 682, _("Saudi Arabia")
    SB = 90, _("Solomon Islands")
    SC = 690, _("Seychelles")
    SD = 729, _("Sudan")
    SE = 752, _("Sweden")
    SG = 702, _("Singapore")
    SH = 654, _("St. Helena")
    SI = 705, _("Slovenia")
    SJ = 744, _("Svalbard And Jan Mayen Islands")
    SK = 703, _("Slovakia (Slovak Republic)")
    SL = 694, _("Sierra Leone")
    SM = 674, _("San Marino")
    SN = 686, _("Senegal")
    SO = 706, _("Somalia")
    SR = 740, _("Suriname")
    ST = 678, _("Sao Tome And Principe")
    SV = 222, _("El Salvador")
    SY = 760, _("Syrian Arab Republic")
    SZ = 748, _("Swaziland")
    TC = 796, _("Turks And Caicos Islands")
    TD = 148, _("Chad")
    TF = 260, _("French Southern Territories")
    TG = 768, _("Togo")
    TH = 764, _("Thailand")
    TJ = 762, _("Tajikistan")
    TK = 772, _("Tokelau")
    TM = 795, _("Turkmenistan")
    TN = 788, _("Tunisia")
    TO = 776, _("Tonga")
    TP = 626, _("East Timor")
    TR = 792, _("Turkey")
    TT = 780, _("Trinidad And Tobago")
    TV = 798, _("Tuvalu")
    TW = 158, _("Taiwan, Province Of China")
    TZ = 834, _("United Republic Of Tanzania")
    UA = 804, _("Ukraine")
    UG = 800, _("Uganda")
    UM = 581, _("United States Minor Outlying Islands")
    US = 840, _("United States")
    UY = 858, _("Uruguay")
    UZ = 860, _("Uzbekistan")
    VA = 336, _("Holy See (Vatican City State)")
    VC = 670, _("Saint Vincent And The Grenadines")
    VE = 862, _("Venezuela")
    VG = 92, _("Virgin Islands (British)")
    VI = 850, _("Virgin Islands (U.S.)")
    VN = 704, _("Viet Nam")
    VU = 548, _("Vanuatu")
    WF = 876, _("Wallis And Futuna Islands")
    WS = 882, _("Samoa")
    YE = 887, _("Yemen")
    YT = 175, _("Mayotte")
    ZA = 710, _("South Africa")
    ZM = 894, _("Zambia")
    ZW = 716, _("Zimbabwe")


class USAStateChoices(models.TextChoices):
    ALABAMA = "AL", _("Alabama")
    ALASKA = "AK", _("Alaska")
    ARIZONA = "AZ", _("Arizona")
    ARKANSAS = "AR", _("Arkansas")
    CALIFORNIA = "CA", _("California")
    COLORADO = "CO", _("Colorado")
    CONNECTICUT = "CT", _("Connecticut")
    DELAWARE = "DE", _("Delaware")
    DISTRICT_OF_COLUMBIA = "DC", _("District of Columbia")
    FLORIDA = "FL", _("Florida")
    GEORGIA = "GA", _("Georgia")
    HAWAII = "HI", _("Hawaii")
    IDAHO = "ID", _("Idaho")
    ILLINOIS = "IL", _("Illinois")
    INDIANA = "IN", _("Indiana")
    IOWA = "IA", _("Iowa")
    KANSAS = "KS", _("Kansas")
    KENTUCKY = "KY", _("Kentucky")
    LOUISIANA = "LA", _("Louisiana")
    MAINE = "ME", _("Maine")
    MARYLAND = "MD", _("Maryland")
    MASSACHUSETTS = "MA", _("Massachusetts")
    MICHIGAN = "MI", _("Michigan")
    MINNESOTA = "MN", _("Minnesota")
    MISSISSIPPI = "MS", _("Mississippi")
    MISSOURI = "MO", _("Missouri")
    MONTANA = "MT", _("Montana")
    NEBRASKA = "NE", _("Nebraska")
    NEVADA = "NV", _("Nevada")
    NEW_HAMPSHIRE = "NH", _("New Hampshire")
    NEW_JERSEY = "NJ", _("New Jersey")
    NEW_MEXICO = "NM", _("New Mexico")
    NEW_YORK = "NY", _("New York")
    NORTH_CAROLINA = "NC", _("North Carolina")
    NORTH_DAKOTA = "ND", _("North Dakota")
    OHIO = "OH", _("Ohio")
    OKLAHOMA = "OK", _("Oklahoma")
    OREGON = "OR", _("Oregon")
    PENNSYLVANIA = "PA", _("Pennsylvania")
    RHODE_ISLAND = "RI", _("Rhode Island")
    SOUTH_CAROLINA = "SC", _("South Carolina")
    SOUTH_DAKOTA = "SD", _("South Dakota")
    TENNESSEE = "TN", _("Tennessee")
    TEXAS = "TX", _("Texas")
    UTAH = "UT", _("Utah")
    VERMONT = "VT", _("Vermont")
    VIRGINIA = "VA", _("Virginia")
    WASHINGTON = "WA", _("Washington")
    WEST_VIRGINIA = "WV", _("West Virginia")
    WISCONSIN = "WI", _("Wisconsin")
    WYOMING = "WY", _("Wyoming")