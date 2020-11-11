# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # def button_mark_done(self):
    #     self.ensure_one()
    #     self._check_company()
    #     # for wo in self.workorder_ids:
    #     #     if wo.time_ids.filtered(lambda x: (not x.date_end) and (x.loss_type in ('productive', 'performance'))):
    #     #         raise UserError(_('Work order %s is still running') % wo.name)
    #     self._check_lots()
    #
    #     self.post_inventory()
    #     # Moves without quantity done are not posted => set them as done instead of canceling. In
    #     # case the user edits the MO later on and sets some consumed quantity on those, we do not
    #     # want the move lines to be canceled.
    #     (self.move_raw_ids | self.move_finished_ids).filtered(lambda x: x.state not in ('done', 'cancel')).write({
    #         'state': 'done',
    #         'product_uom_qty': 0.0,
    #     })
    #     return self.write({'date_finished': fields.Datetime.now()})
    #
    # @api.depends('move_raw_ids.state', 'move_finished_ids.state', 'workorder_ids', 'workorder_ids.state', 'qty_produced', 'move_raw_ids.quantity_done', 'product_qty')
    # def _compute_state(self):
    #     """ Compute the production state. It use the same process than stock
    #     picking. It exists 3 extra steps for production:
    #     - planned: Workorder has been launched (workorders only)
    #     - progress: At least one item is produced.
    #     - to_close: The quantity produced is greater than the quantity to
    #     produce and all work orders has been finished.
    #     """
    #     # TODO: duplicated code with stock_picking.py
    #     for production in self:
    #         if not production.move_raw_ids:
    #             production.state = 'draft'
    #         elif all(move.state == 'draft' for move in production.move_raw_ids):
    #             production.state = 'draft'
    #         elif all(move.state == 'cancel' for move in production.move_raw_ids):
    #             production.state = 'cancel'
    #         # elif all(move.state in ['cancel', 'done'] for move in production.move_raw_ids):
    #         #     production.state = 'done'
    #         elif production.move_finished_ids.filtered(lambda m: m.state not in ('cancel', 'done') and m.product_id.id == production.product_id.id)\
    #              and (production.qty_produced >= production.product_qty)\
    #              and (not production.routing_id or all(wo_state in ('cancel', 'done') for wo_state in production.workorder_ids.mapped('state'))):
    #             production.state = 'to_close'
    #         elif production.workorder_ids and any(wo_state in ('progress') for wo_state in production.workorder_ids.mapped('state'))\
    #              or production.qty_produced > 0 and production.qty_produced < production.product_uom_qty:
    #             production.state = 'progress'
    #         elif production.workorder_ids:
    #             production.state = 'planned'
    #         else:
    #             production.state = 'confirmed'
    #         production.state = 'progress'
    #         # Compute reservation state
    #         # State where the reservation does not matter.
    #         if production.state in ('draft', 'done', 'cancel'):
    #             production.reservation_state = False
    #         # Compute reservation state according to its component's moves.
    #         # else:
    #         #     relevant_move_state = production.move_raw_ids._get_relevant_state_among_moves()
    #         #     if relevant_move_state == 'partially_available':
    #         #         if production.routing_id and production.routing_id.operation_ids and production.bom_id.ready_to_produce == 'asap':
    #         #             production.reservation_state = production._get_ready_to_produce_state()
    #         #         else:
    #         #             production.reservation_state = 'confirmed'
    #         #     elif relevant_move_state != 'draft':
    #         #         production.reservation_state = relevant_move_state
