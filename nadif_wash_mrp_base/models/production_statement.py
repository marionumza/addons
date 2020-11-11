# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, time
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ProductionStatement(models.Model):
    _name = 'production.statement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Production Statement'

    name = fields.Char(string="Sequence", default="/", required=True)
    type = fields.Selection([
        ('finished', 'Finished Product'),
        ('semi_finished', 'Semi Finished'),
        ], string='Type', required=True)
    hour_range_id = fields.Many2one('planning.slot.template', 'Time Range')
    line_range_id = fields.Many2one('planning.slot.line', 'Line Range')
    date_start = fields.Date(string="Date Start", default=fields.Date.today)
    date_finished = fields.Date(string="Date Finished")
    line_ids = fields.One2many('production.statement.line', 'statement_id', string="Production Statement Lines")
    production_count = fields.Integer('# Manufacturing Orders',
                               compute='_compute_production_count', compute_sudo=False)
    finished_product_count = fields.Integer('# Finished Products',
                               compute='_compute_finished_product_count', compute_sudo=False)
    raw_product_count = fields.Integer('# Raw Products',
                               compute='_compute_raw_product_count', compute_sudo=False)
    total_qty = fields.Float('Total Quantity', digits='Product Unit of Measure', compute='_compute_qty_totals')
    total_scrap  = fields.Float('Total Scrap', digits='Product Unit of Measure', compute='_compute_qty_totals')

    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].next_by_code('production.statement') or '/'
        vals['name'] = seq
        return super(ProductionStatement, self).create(vals)

    def do_generate(self):
        for rec in self:
            res = []
            rec.line_ids.unlink()
            workcenter_ids = self.env['mrp.workcenter'].search([('type', '=', rec.type)])
            for workcenter in workcenter_ids:
                if workcenter.product_ids:
                    product_id = workcenter.product_ids.sorted(key=lambda r: r.sequence)[0]
                    vals = {
                        'workcenter_id': workcenter.id,
                        'employee_id': workcenter.employee_ids and workcenter.employee_ids[0].id,
                        'hour_range_id': rec.hour_range_id.id,
                        'date': rec.date_start,
                        'workcenter_product_id': product_id.id
                    }
                    res.append((0, 0, vals))
                else:
                    vals = {
                        'workcenter_id': workcenter.id,
                        'employee_id': workcenter.employee_ids and workcenter.employee_ids[0].id,
                        'hour_range_id': rec.hour_range_id.id,
                        'date': rec.date_start,
                    }
                    res.append((0, 0, vals))
            rec.line_ids = res

    def do_produce(self):
        for rec in self:
            rec.line_ids.do_produce()

    def _compute_qty_totals(self):
        for rec in self:
            rec.total_qty = sum(rec.line_ids.mapped('qty'))
            rec.total_scrap = sum(rec.line_ids.mapped('scrap'))

    def _compute_production_count(self):
        for production in self:
            line_ids = self.env['production.statement.line'].search([('statement_id', '=', production.id)])
            production.production_count = self.env['mrp.production'].search_count([('id', 'in', line_ids.mapped('production_id').ids)])

    def _compute_finished_product_count(self):
        for product in self:
            line_ids = self.env['production.statement.line'].search([('statement_id', '=', product.id)])
            production_ids = line_ids.mapped('production_id')
            product.finished_product_count = self.env['stock.move.line'].search_count([('id', 'in', production_ids.mapped('finished_move_line_ids').ids)])

    def _compute_raw_product_count(self):
        for product in self:
            line_ids = self.env['production.statement.line'].search([('statement_id', '=', product.id)])
            production_ids = line_ids.mapped('production_id')
            product.raw_product_count = self.env['stock.move'].search_count([('id', 'in', production_ids.mapped('move_raw_ids').ids)])

    def action_open_production(self):
        action = {
            'name': _('Manufacturing Orders'),
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
        }
        # template_ids = self.mapped('product_tmpl_id').ids
        # action['context'] = {
        #     'default_product_id': self.product_variant_ids.ids[0],
        # }
        line_ids = self.env['production.statement.line'].search([('statement_id', '=', self.id)])
        action['domain'] = [('id', 'in', line_ids.mapped('production_id').ids)]
        return action

    def action_open_finished_product(self):
        action = {
            'name': _('Finished Products'),
            'res_model': 'stock.move.line',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
        }
        # template_ids = self.mapped('product_tmpl_id').ids
        # action['context'] = {
        #     'default_product_id': self.product_variant_ids.ids[0],
        # }
        line_ids = self.env['production.statement.line'].search([('statement_id', '=', self.id)])
        production_ids = line_ids.mapped('production_id')
        action['domain'] = [('id', 'in', production_ids.mapped('finished_move_line_ids').ids)]
        return action

    def action_open_raw_product(self):
        action = {
            'name': _('Raw Products'),
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
        }
        # template_ids = self.mapped('product_tmpl_id').ids
        # action['context'] = {
        #     'default_product_id': self.product_variant_ids.ids[0],
        # }
        line_ids = self.env['production.statement.line'].search([('statement_id', '=', self.id)])
        production_ids = line_ids.mapped('production_id')
        action['domain'] = [('id', 'in', production_ids.mapped('move_raw_ids').ids)]
        action['context'] = {'search_default_by_product': 1}
        return action


class ProductionStatementLine(models.Model):
    _name = 'production.statement.line'
    _description = 'Production Statement Line'
    _rec_name = 'workcenter_id'

    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', required=True)
    date = fields.Date("Date")
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    employee_id = fields.Many2one('hr.employee', 'Operator')
    qty = fields.Float('Quantity', digits='Product Unit of Measure')
    scrap  = fields.Float('Scrap', digits='Product Unit of Measure')
    statement_id = fields.Many2one('production.statement', 'Production Statement')
    hour_range_id = fields.Many2one('planning.slot.template', 'Time Range')
    workcenter_product_id = fields.Many2one(
        'mrp.workcenter.product')
    date_finished = fields.Date(string="Date Finished")
    loss_id = fields.Many2one(
        'mrp.workcenter.productivity.loss', "Loss Reason")
    loss_time = fields.Float('Loss time', default=0)
    loss_description = fields.Text('Description')
    working_state = fields.Selection([
        ('normal', 'Normal'),
        ('blocked', 'Blocked'),
        ('done', 'In Progress')], 'Workcenter Status', compute='_compute_working_state', store=True)

    @api.depends('loss_time','loss_id')
    def _compute_working_state(self):
        for rec in self:
            if rec.loss_id and rec.loss_time:
                rec.working_state = 'blocked'
            else:
                rec.working_state = 'normal'

    def act_mrp_block_workcenter(self):
        self.ensure_one()
        return {
                'type': 'ir.actions.act_window',
                'name': _('Block Workcenter'),
                'view_mode': 'form',
                'res_id': self.id,
                'context': {'default_working_state': 'blocked',},
                'res_model': 'production.statement.line',
                'view_id': self.env.ref('nadif_wash_mrp_base.mrp_workcenter_block_wizard_form').id,
                'target': 'new',
                }

    def unblock(self):
        self.ensure_one()
        # if self.working_state != 'blocked':
        #     raise UserError(_("It has already been unblocked."))
        # times = self.env['mrp.workcenter.productivity'].search([('workcenter_id', '=', self.workcenter_id.id), ('date_end', '=', False)])
        # times.write({'date_end': fields.Datetime.now()})
        # # return {'type': 'ir.actions.client', 'tag': 'reload'}
        return

    def do_produce(self):
        for line in self:
            if line.qty and not line.production_id:
                t = time(int(line.statement_id.line_range_id.start_time)-1, 0)
                date = datetime.combine(line.date, t)
                product_id = line.workcenter_product_id.product_id
                production_id = self.env['mrp.production'].create({
                    'product_id': product_id.id,
                    'bom_id': line.workcenter_product_id.bom_id.id,
                    'product_uom_id': line.workcenter_product_id.bom_id.product_uom_id.id,
                    'date_planned_start': date,
                    'date_planned_finished': date + timedelta(hours=line.statement_id.line_range_id.duration),
                    'product_qty': line.qty,})

                production_id._onchange_move_raw()
                production_id.product_qty = line.qty
                production_id.routing_id = line.workcenter_product_id.bom_id.routing_id.id
                production_id.action_confirm()
                production_id.button_plan()
                production_id.workorder_ids[0].write({
                    'date_planned_finished': date + timedelta(hours=line.statement_id.line_range_id.duration),
                    'date_planned_start': date,
                    'new_qty_producing': line.qty + line.scrap,
                    'qty_producing': line.qty + line.scrap,

                })
                loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'productive')],
                                                                              limit=1)
                productive_duration = line.statement_id.line_range_id.duration
                if line.loss_time and line.loss_id:
                    production_id.workorder_ids[0].time_ids = [(0, 0, {
                        'date_start': date,
                        'date_end': date + timedelta(hours=line.loss_time),
                        'employee_id': line.employee_id.id,
                        'loss_id': line.loss_id.id,
                        'description': line.loss_description,
                        'workcenter_id': line.workcenter_id.id,
                        'workorder_id': production_id.workorder_ids[0].id
                    })]
                    productive_duration = line.statement_id.line_range_id.duration - line.loss_time

                production_id.workorder_ids[0].time_ids = [(0, 0, {
                    'date_start': date,
                    'date_end': date + timedelta(hours=productive_duration),
                    'employee_id': line.employee_id.id,
                    'loss_id': loss_id.id,
                    'workcenter_id': line.workcenter_id.id,
                    'workorder_id':production_id.workorder_ids[0].id
                })]
                production_id.workorder_ids[0].do_finish()
                production_id.button_mark_done()

                line.production_id = production_id
                line.workorder_id = production_id.workorder_ids[0]
