# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_grant_ids = fields.One2many('sale.grant', 'sale_order_id', string="Sale grants")

    def action_view_grants(self):
        self.ensure_one()
        action = self.env.ref('nadif_wash_base.sale_grant_action').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {'default_sale_order_id': self.id,
                             }
        return action