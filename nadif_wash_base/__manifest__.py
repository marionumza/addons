# -*- coding: utf-8 -*-
{
    'name': "Nadif Wash Base",
    'summary': """This module is use for nadif wash base""",
    'description': """ Nadif Wash Base """,
    'author': "PYVAL",
    'website': "https://pyval.com/",
    'category': 'Grant',
    'version': '13.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'sale_management', 'stock', 'kzm_payroll_ma'],

    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "data/sale_grant_sequence.xml",
        "views/sale_grant_views.xml",
        "views/sale_order_inherit_views.xml",
        "views/stock_picking_views.xml",
        "views/hr_employee_views.xml",
    ],
}
