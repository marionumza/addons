# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class pos_config(models.Model):
    _inherit = "pos.config"

    show_operating_unit = fields.Boolean('Show operating unit',
                                         help='Show operating unit in POS ticket',
                                         default=1)
