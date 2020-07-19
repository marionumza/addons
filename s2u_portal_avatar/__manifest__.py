{
    'name': 'Portal Avatar',
    'version': '13.0.1.0',
    'author': 'Solutions2use',
    'price': 0.0,
    'currency': 'EUR',
    'maintainer': 'Solutions2use',
    'support': 'info@solutions2use.com',
    'images': ['static/description/app_logo.jpg'],
    'license': 'OPL-1',
    'website': 'https://www.solutions2use.com',
    'category':  'Website',
    'summary': 'This module allows portal user to add/change/delete his avatar (profile picture).',
    'description':
        """This module allows portal user to add/change/delete his avatar (profile picture).
        """,
    'depends': ['base', 'portal'],
    'data': [
        'views_inherited/ir_qweb_widget_templates.xml',
        'views_inherited/portal_templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}
