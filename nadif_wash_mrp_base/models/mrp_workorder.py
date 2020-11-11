# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools import float_compare, float_round
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def button_finish(self):
        self.ensure_one()
        self.end_all()
        end_date = datetime.now()
        return self.write({
            'state': 'done',
            'date_finished': end_date,
            'date_planned_finished': end_date
        })


    # def record_production(self):
    #     if not self:
    #         return True
    #
    #     self.ensure_one()
    #     self._check_company()
    #     if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
    #         raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))
    #
    #     # If last work order, then post lots used
    #     # if not self.next_work_order_id:
    #     #     self._update_finished_move()
    #
    #     # Transfer quantities from temporary to final move line or make them final
    #     self._update_moves()
    #
    #     # Transfer lot (if present) and quantity produced to a finished workorder line
    #     if self.product_tracking != 'none':
    #         self._create_or_update_finished_line()
    #
    #     # Update workorder quantity produced
    #     self.qty_produced += self.qty_producing
    #
    #     # Suggest a finished lot on the next workorder
    #     if self.next_work_order_id and self.product_tracking != 'none' and (
    #         not self.next_work_order_id.finished_lot_id or self.next_work_order_id.finished_lot_id == self.finished_lot_id):
    #         self.next_work_order_id._defaults_from_finished_workorder_line(self.finished_workorder_line_ids)
    #         # As we may have changed the quantity to produce on the next workorder,
    #         # make sure to update its wokorder lines
    #         self.next_work_order_id._apply_update_workorder_lines()
    #
    #     # One a piece is produced, you can launch the next work order
    #     self._start_nextworkorder()
    #
    #     # Test if the production is done
    #     rounding = self.production_id.product_uom_id.rounding
    #     if float_compare(self.qty_produced, self.production_id.product_qty, precision_rounding=rounding) < 0:
    #         previous_wo = self.env['mrp.workorder']
    #         if self.product_tracking != 'none':
    #             previous_wo = self.env['mrp.workorder'].search([
    #                 ('next_work_order_id', '=', self.id)
    #             ])
    #         candidate_found_in_previous_wo = False
    #         if previous_wo:
    #             candidate_found_in_previous_wo = self._defaults_from_finished_workorder_line(
    #                 previous_wo.finished_workorder_line_ids)
    #         if not candidate_found_in_previous_wo:
    #             # self is the first workorder
    #             self.qty_producing = self.qty_remaining
    #             self.finished_lot_id = False
    #             if self.product_tracking == 'serial':
    #                 self.qty_producing = 1
    #
    #         self._apply_update_workorder_lines()
    #     else:
    #         self.qty_producing = 0
    #         self.button_finish()
    #     return True
