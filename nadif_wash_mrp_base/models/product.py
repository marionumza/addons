# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    statement_line_count = fields.Integer('# Production Statement Lines',
                               compute='_compute_statement_line_count', compute_sudo=False)

    def _compute_statement_line_count(self):
        for product in self:
            product.statement_line_count = self.env['production.statement.line'].search_count([('workcenter_product_id.product_id', 'in', product.product_variant_ids.ids)])

    def action_open_production_statement_line(self):
        action =  {
            'name': _('Production Statement Lines'),
            'res_model': 'production.statement.line',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
        }
        # template_ids = self.mapped('product_tmpl_id').ids
        # action['context'] = {
        #     'default_product_id': self.product_variant_ids.ids[0],
        # }
        action['domain'] = [('workcenter_product_id.product_id', 'in', self.product_variant_ids.ids)]
        return action


class ProductProduct(models.Model):
    _inherit = 'product.product'

    statement_line_count = fields.Integer('# Production Statement Lines',
                               compute='_compute_statement_line_count', compute_sudo=False)

    def _compute_statement_line_count(self):
        for product in self:
            product.statement_line_count = self.env['production.statement.line'].search_count([('workcenter_product_id.product_id', '=', product.id)])

    def action_open_production_statement_line(self):
        action =  {
            'name': _('Production Statement Lines'),
            'res_model': 'production.statement.line',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
        }
        # template_ids = self.mapped('product_tmpl_id').ids
        # action['context'] = {
        #     'default_product_id': self.id,
        # }
        action['domain'] = [('workcenter_product_id.product_id', '=', self.id)]
        return action