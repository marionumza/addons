# -*- coding: utf-8 -*-
{
    'name': 'Data Clear',
    'category': 'Extra Tools',
    'author':'kreatif Solution ',
    'sequence': 1,
    'summary': """A powerful testing tool.Easily clear any odoo object data what you want. """,
    'website': 'www.kreatifsolution.com',
    'description': """Business Testing Data Clear. You can define default model group list by yourself to help your work. """,


    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'data/clear_data.xml',
        'security/ir.model.access.csv',
        'views/clear_data_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
}
