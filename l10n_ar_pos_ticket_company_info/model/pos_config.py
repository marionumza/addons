# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class pos_config(models.Model):
    _inherit = "pos.config"

    show_report_header = fields.Boolean('Show report header',
    	                                   help='Show report company header in POS ticket',
    	                                   default=1)
    show_report_company_name = fields.Boolean('Show report company name',
    	                                         help='Show report company name in POS ticket',
    	                                         default=1)
