# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

{
    'name': 'POS Promotion',
    'category': 'Point of Sale',
    'summary' : "Point of Sale Promotion",
    'description': """
User needs to create the promotion according to promotion, rules will be apply in POS.
""",
    'author': "Acespritech Solutions Pvt. Ltd.",
    'website': "www.acespritech.com",
    'depends': ['web', 'point_of_sale','sale_management'],
    'price': 35.0,
    'currency': 'EUR',
    'version': '1.0',
    'images': ['static/description/main_screenshot.png'],
    'data': [
        'views/pos_promotion_view.xml',
        'views/promotion_template.xml',
        'views/product_brand_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'test': [],
    'qweb': ['static/src/xml/promotion.xml'],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: