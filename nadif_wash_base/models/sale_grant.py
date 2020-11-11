# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleGrant(models.Model):
    _name = 'sale.grant'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sale Grant'

    name = fields.Char(string="Sequence", default="/", required=True)
    sale_order_id = fields.Many2one('sale.order', string="Sale order", domain="[('state','=','sale')]")
    partner_id = fields.Many2one('res.partner', string="Customer", related="sale_order_id.partner_id")
    date = fields.Datetime(string="Date", default=fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="The company's currency", readonly=True,
                                  related='company_id.currency_id', store=True)
    total_invoice = fields.Monetary(string="Total invoice", compute='compute_total_invoice')
    total_order = fields.Monetary(string="Total order", related="sale_order_id.amount_total")
    sale_order_invoice_ids = fields.Many2many('account.move', related='sale_order_id.invoice_ids')
    invoice_ids = fields.Many2many('account.move', 'invoice_grant_rel', string="Invoices")
    sale_order_delivery_ids = fields.One2many('stock.picking', related='sale_order_id.picking_ids')
    delivery_ids = fields.Many2many('stock.picking', 'delivery_grant_rel', string="Deliveries",
                                    domain="[('id', 'in', sale_order_id.picking_ids.ids)]")
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'hr.applicant')],
                                     string='Attachments')

    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].next_by_code('sale.grant') or '/'
        vals['name'] = seq
        res = super(SaleGrant, self).create(vals)
        return res

    @api.depends('invoice_ids')
    def compute_total_invoice(self):
        total = 0
        for rec in self:
            if rec.invoice_ids:
                invoices = self.env['account.move'].search([('id', 'in', rec.invoice_ids.ids)])
                for inv in invoices:
                    total = total + inv.amount_total
            rec.total_invoice = total

    def invoices_tree_view_obj(self):
        self.ensure_one()
        action = self.env.ref('nadif_wash_base.invoices_tree_action').read()[0]
        action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        return action

    def deliveries_tree_view_obj(self):
        self.ensure_one()
        action = self.env.ref('nadif_wash_base.deliveries_tree_action').read()[0]
        action['domain'] = [('id', 'in', self.delivery_ids.ids)]
        return action

    def docs_tree_view_obj(self):
        self.ensure_one()
        action = self.env.ref('nadif_wash_base.documents_tree_action').read()[0]
        action['domain'] = [('id', 'in', self.delivery_ids.ids)]
        return action


class AccountMove(models.Model):
    _inherit = 'account.move'

    grant_ids = fields.Many2many('sale.grant', 'invoice_grant_rel', string="Grants")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    grant_ids = fields.Many2many('sale.grant', 'delivery_grant_rel', string="Grants")
