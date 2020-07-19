{
    'name': "Autoincrement References",
    'summary': """Creates auto incremented references for partners and products""",

    'author': "Arxi",
    'website': "http://www.arxi.pt",

    'category': 'Tools',
    'version': '13.0.0.0.1',
    'license': 'OPL-1',

    'price': 0.00,
    'currency': 'EUR',

    'depends': ['account'],

    'data': [
        'views/res_config_settings_views.xml',
        'data/config_param.xml'
    ],

    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
    ],
}
