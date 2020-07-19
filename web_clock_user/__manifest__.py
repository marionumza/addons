# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2019  Erlangga Indra Permana  (https://erlaangga.github.io)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Clock',
    'version': '1.0',
    'category': 'Web',
    'summary': 'Web Clock',
    'author': 'Erlangga Indra Permana',
    'website': 'https://erlaangga.github.io',
    'license': 'LGPL-3',
    'depends': [
        'web'
    ],
    'data': [
        'views/user_preference_views.xml',
        'views/webclient_templates.xml'
    ],
    'qweb': [
        "static/src/xml/clock.xml",
    ],
    'images':['static/description/banner.png'],
    'application': True,
}