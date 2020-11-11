# -*- coding: utf-8 -*-
{
    'name': "Nadif Wash MRP Base",
    'summary': """This module is use for nadif wash base""",
    'description': """ Nadif Wash MRP Base """,
    'author': "PYVAL",
    'website': "https://pyval.com/",
    'category': 'mrp',
    'version': '13.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mrp', 'bi_change_mrp_qty', 'kzm_planning_slot'],

    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "data/production_statement_sequence.xml",
        "views/production_statement_views.xml",
        "views/mrp_workcenter_views.xml",
        "views/mrp_workorder_views.xml",
        "views/product_views.xml",
    ],
}
