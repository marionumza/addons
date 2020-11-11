# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    employee_ids = fields.One2many('hr.employee', 'workcenter_id', string='Employees')
    type = fields.Selection([
        ('finished', 'Finished Product'),
        ('semi_finished', 'Semi Finished'),
    ], string='Type')
    product_ids = fields.Many2many('mrp.workcenter.product', 'rel_mrp_workcenter_product', string='Authorized Products')


class MrpWorkcenterProductivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    employee_id = fields.Many2one('hr.employee', string='Employee')


class MrpWorkcenterProduct(models.Model):
    _name = 'mrp.workcenter.product'
    _descirption = 'Authorized Products'
    _rec_name = 'product_id'

    sequence = fields.Integer('Sequence', default=20)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company)
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="[('bom_ids', '!=', False), ('bom_ids.active', '=', True), ('bom_ids.type', '=', 'normal'), ('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=True, check_company=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id', readonly=False)
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        domain="""[
                '|',
                    ('product_id', '=', product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids', '=', product_id),
                        ('product_id','=',False),
                ('type', '=', 'normal'),
                '|',
                    ('company_id', '=', company_id),
                    ('company_id', '=', False)
                ]
        """,
        required=True, check_company=True)
    # routing_id = fields.Many2one('mrp.routing', 'Parent Routing', required=True)
    workcenter_ids = fields.Many2many('mrp.workcenter', 'rel_mrp_workcenter_product', string='Workcenters')
