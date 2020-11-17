# -*- coding: utf-8 -*-

{
    'name': 'Imazighen Enterprise Backend Theme',
    'category': 'Themes/Backend',
    'version': '13.1',
    'summary': """ Odoo Enterprise Backend Theme For Community Edition""",
    'description':
        """
Theme Enterprise Web Client.
===========================

This module modifies the web addon to provide Enterprise design and responsiveness.
        """,
    "author": "Imazighen",
    "price": "69",
    "currency": "EUR",
    "support": "imazighenapps@gmail.com",
    'depends': ['web'],
    'auto_install': True,
    'data': [
        'views/webclient_templates.xml',
    ],
   "images": [
        'static/description/panelz.png',
      
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
     "license": "OPL-1",
}
