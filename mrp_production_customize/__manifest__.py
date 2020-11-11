# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016-Today Geminate Consultancy Services (<http://geminatecs.com>).
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
    'name' : 'Mrp Production Customize',
    'version' : '13.0.0.1',
    'author': 'Geminate Consultancy Services',
    'company': 'Geminate Consultancy Services',
    'category': 'Manufacturing',
    'website': 'https://www.geminatecs.com/',
    'summary' : 'Mrp Production Work flow Customize',
    'description' : """  This module features to control the mrp production flow using partial processing on Manufacturing Order and Work orders based on product quantity. """,
    "license": "Other proprietary",
    'depends' : ['mrp','stock','mrp_workorder','mrp_account'],
    'data' : [
        'data/stock_data.xml',
        'wizard/mrp_immediate_transfer_views.xml',
        'views/mrp_production_view.xml',
        'views/mrp_workorder_view.xml',
    ],
    'demo': [],
    'price': '249.99',
    'currency': 'EUR',
    'installable' : True,
    'application' : False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
