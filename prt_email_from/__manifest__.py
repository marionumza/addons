# -*- coding: utf-8 -*-
{
    'name': 'Email From Settings: Customize Email From Field',
    'version': '13.0.1.0.0',
    'summary': """Customize 'from' and 'reply-to' addresses for email messages sent from Odoo""",
    'author': 'Ivan Sokolov, Cetmix',
    'category': 'Productivity',
    'license': 'LGPL-3',
    'website': 'https://cetmix.com',
    'description': """    
    Use company email address for outgoing email messages (Some User <some.user@privatemail.com> -> Some User <mycompany@companydomain.com>)_\n
    Add company name to sender's name in 'From' (Some User <mycompany@companydomain.com> -> Some User via My Company <mycompany@companydomain.com>)\n
    Add sender's name to company name in 'Reply-to' (My Company <mycompany@companydomain.com> -> Some User via My Company <mycompany@companydomain.com>)\n
    Set names joint for 'From' and 'Reply-to' (Some User My Company <mycompany@companydomain.com> -> Some User via My Company <mycompany@companydomain.com>)\n
    Use custom "from" address for Odoo models (Pro Version)_\n              
""",
    'depends': ['base', 'mail'],
    'images': ['static/description/banner.png'],

    'data': [
        'views/res_company.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
