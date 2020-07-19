# -*- coding: utf-8 -*-
{
    'name': "odoo_mo_top_salespersons",

    'summary': """
       Get Report Contains Top SalesPerson  in Html , xls , Pdf , You can also Preview before you Print""",

    'description': """
        Get Report Contains Top SalesPerson  in Html , xls , Pdf , You can also Preview before you Print
    """,

    'author': "Odoo Mo",
    'website': "https://www.facebook.com/groups/246493319957599/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'sales',
    'version': '13.0',
    'license': 'AGPL-3',
    'images': ['static/description/1.png'],

    # any module necessary for this one to work correctly
    'depends': ['base','sale','report_xlsx','sale_management'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'templates.xml',
        'wizards/wizard_view.xml',
        'reports/template.xml',
        'reports/report.xml',
    ],
'qweb': [
        'static/src/xml/report_tmpl.xml'],
    # only loaded in demonstration mode

}
