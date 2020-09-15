# -*- coding: utf-8 -*-
{
    'name': 'POS ticket company info',
    'version': '0.1',
    'author': 'Cumbre Gestión en Software',
    'license': 'LGPL-3',
    'category': 'Point Of Sale',
    'website': 'https://cumbre.net/',
    'depends': ['point_of_sale', 'l10n_ar_pos_einvoice_ticket'],
    'data': [
        'views/pos_assets.xml',
        'views/pos_config.xml',
    ],
    'qweb': [
        'static/src/xml/pos_ticket.xml',
        'static/src/xml/xml_receipt.xml',
    ],
    'installable': True,
}
