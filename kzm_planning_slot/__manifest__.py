# -*- coding: utf-8 -*-
{
    'name': "KZM Planning Slot",
    'summary': """KZM Planning Slot Lines""",
    'description': """ KZM Planning Slot Lines """,
    'author': "KARIZMA",
    'website': "https://karizma.ma/",
    'category': 'planning',
    'version': '13.0',

    # any module necessary for this one to work correctly
    'depends': ['planning'],

    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "views/planning_views.xml",
    ],
}
