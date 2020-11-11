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


from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from dateutil.relativedelta import relativedelta
import math


class MrpProductProduce(models.TransientModel):
    _inherit = "mrp.product.produce"



    def _record_production(self):
        main_product_moves = self.production_id.move_finished_ids.filtered(lambda x: x.product_id.id == self.production_id.product_id.id)
        todo_quantity = self.production_id.product_qty - sum(main_product_moves.mapped('quantity_done'))
        
        if (todo_quantity != 0 or todo_quantity == 0):
            quantity = self.qty_producing
            workorder_ids = self.production_id.workorder_ids.filtered(lambda x: x.state != 'done')
            if workorder_ids:
#                 # Virtual Locations/Production -> Stock
                production_move_finished_id = self.move_finished_ids.filtered(
                                lambda x: (x.product_id.id == self.product_id.id) and (x.state not in ('done', 'cancel')))
                
                if production_move_finished_id:
                    production_move_finished_id.update({'quantity_done': 0.0})
                workorder_ids.update({'qty_producing': 0.0, 'qty_production_wo': quantity, 'qty_production_dup': quantity})
           
# 
#                 # Create Internal Transfer for based on lots wit use of Production nventory moves
                for pl in self._workorder_line_ids():
                    if pl.product_tracking == 'serial':
                        qty_to_consume = float_round(self.qty_producing * pl.move_id.unit_factor, precision_rounding=pl.move_id.product_uom.rounding)
                        
                        #New Code 23march
                        current_lot_move_line = pl.move_id.move_line_ids.filtered(lambda ml:ml.lot_id == pl.lot_id)
                        if current_lot_move_line:
                            current_lot_move_line.update({'lot_id': pl.lot_id.id,'qty_done':1})
                        
                        # Remove Reserved Quant For WH/Stock
                        stock_quant_id = self.env['stock.quant'].search([
                            ('product_id', '=', pl.move_id.product_id.id),
                            ('location_id', '=', self.production_id.location_src_id.id),
                            ('reserved_quantity', '>', 0.0)
                        ])
                        if stock_quant_id:
                            stock_quant_id.sudo().update({'reserved_quantity': 0.0})
# 
                        source_location = pl.move_id.move_line_ids[0].location_id # source_location = 16
                        destination_location = pl.move_id.move_line_ids[0].location_dest_id # destination_location = 67
                        internal_transfer_pick = self.env['stock.picking'].create({
                            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                            'location_id': source_location.id,
                            'location_dest_id': destination_location.id,
                            'origin': self.production_id.name,
                            'move_lines': [(0, 0, {
                                'name': self.production_id.name,
                                'product_id': pl.move_id.product_id.id,
                                'product_uom_qty': 1,
                                'product_uom': pl.move_id.product_uom.id,
                                'location_id':  destination_location.id,
                                'location_dest_id': source_location.id,
                            })],
                        })
                        immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, internal_transfer_pick.id)]})
                        internal_transfer_pick.action_assign()
                        internal_transfer_pick.move_ids_without_package.move_line_ids.update({'lot_id': current_lot_move_line.lot_id.id})
                        immediate_transfer.process()
#                         # pl.move_id.update({'reserved_availability': qty_to_consume})
                    else:
                        move = self.move_raw_ids.filtered(lambda m: m.id == pl.move_id.id and m.state not in ('done', 'cancel'))
#                         # for state in self.production_id.move_raw_ids:
#                             # for states in state.move_line_ids:
                        qty_to_consume = float_round(self.qty_producing * move.unit_factor, precision_rounding=move.product_uom.rounding)
                        move_lines = self.env['stock.move.line'].search([
                            ('id','in', move.move_line_ids.ids),
                            ('product_id', '=', move.product_id.id),
                            ('reference', '=', self.production_id.name),
                            ('location_dest_id','!=', move.product_id.property_stock_production.id),
                            ('state', '=', 'assigned'),
                        ])
                        if move.product_id.tracking == 'lot':
                            move.move_line_ids.update({'lot_id':pl.lot_id.id, 'qty_done': qty_to_consume})
                            # move.move_line_ids.update({'lot_id':pl.lot_id.id})
                        else:
                            move.move_line_ids.update({'qty_done': qty_to_consume})
                        # Remove Reserved Quant For WH/Stock
                        stock_quant_id = self.env['stock.quant'].search([
                            ('product_id', '=', move.product_id.id),
                            ('location_id', '=', self.production_id.location_src_id.id),
                            ('reserved_quantity', '>', 0.0)
                        ])
                        
                        if stock_quant_id:
                            stock_quant_id.sudo().update({'reserved_quantity': 0.0})
                        for line in move_lines:
                            source_location = line.location_id
                            destination_location = line.location_dest_id
                            internal_transfer_pick = self.env['stock.picking'].create({
                                'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                                'location_id': source_location.id,
                                'location_dest_id': destination_location.id,
                                'origin': self.production_id.name,
                                'move_lines': [(0, 0, {
                                    'name': self.production_id.name,
                                    'product_id': move.product_id.id,
                                    'product_uom_qty': qty_to_consume,
                                    'product_uom': move.product_uom.id,
                                    'location_id':  destination_location.id,
                                    'location_dest_id': source_location.id,
                                    'picking_move_production_id':self.production_id.id
                                    })],
                                })
                            immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, internal_transfer_pick.id)]})
                            internal_transfer_pick.action_assign()
                            
                            #Updates the lot_id which is selected on the wizard.
                            if move.product_id.tracking == 'lot':
                                internal_transfer_pick.move_ids_without_package.move_line_ids.update({'lot_id':pl.lot_id.id})
                            immediate_transfer.process()
                
                #Create Quality check workorderlines from here
                if not self.production_id.workorder_ids.mapped('check_ids'):
                    self.production_id.workorder_ids._create_checks()
                    
                if self.product_id.tracking != 'none':
                    workorder_ids[0].finished_lot_id = self.finished_lot_id
            else:
                quantity = self.production_id.product_uom_id._compute_quantity(quantity, self.production_id.bom_id.product_uom_id) / self.production_id.bom_id.product_qty
                boms, lines = self.production_id.bom_id.explode(self.production_id.product_id, quantity, picking_type=self.production_id.bom_id.picking_type_id)
                workorders = self.env['mrp.workorder']
                original_one = False
                for bom, bom_data in boms:
                    if bom.routing_id.id and (not bom_data['parent_line'] or bom_data['parent_line'].bom_id.routing_id.id != bom.routing_id.id):
                        temp_workorders = self.production_id._workorders_create(bom, bom_data)
                        workorders += temp_workorders
                        if temp_workorders:
                            if original_one:
                                temp_workorders[-1].next_work_order_id = original_one
                            original_one = temp_workorders[0]
                            temp_workorders.update({'qty_producing': 0.0, 'qty_production_wo': quantity, 'is_last_step': True, 'qty_production_dup': quantity})
                # Virtual Locations/Production -> Stock
                production_move_finished_id = self.production_id.move_finished_ids.filtered(
                                lambda x: (x.product_id.id == self.production_id.product_id.id) and (x.state not in ('done', 'cancel')))
                if production_move_finished_id and self.product_id.tracking != 'serial':
                    production_move_finished_id.update({'quantity_done': 0.0})
# 
                # Create Stock -> Physical Locations-1
                # Create Internal Transfer for based on lots wit use of Production nventory moves
                for pl in self._workorder_line_ids():
                    if pl.product_tracking == 'serial':
                        qty_to_consume = float_round(self.qty_producing * pl.move_id.unit_factor, precision_rounding=pl.move_id.product_uom.rounding)
                        
                        #New Code 23march
                        current_lot_move_line = pl.move_id.move_line_ids.filtered(lambda ml:ml.lot_id == pl.lot_id)
                        if current_lot_move_line:
                            current_lot_move_line.update({'lot_id': pl.lot_id.id,'qty_done':1})
                        
                        # Remove Reserved Quant For WH/Stock
                        stock_quant_id = self.env['stock.quant'].search([
                            ('product_id', '=', pl.move_id.product_id.id),
                            ('location_id', '=', self.production_id.location_src_id.id),
                            ('reserved_quantity', '>', 0.0)
                        ])
                        if stock_quant_id:
                            stock_quant_id.sudo().update({'reserved_quantity': 0.0})
# 
                        source_location = pl.move_id.move_line_ids[0].location_id # source_location = 16
                        destination_location = pl.move_id.move_line_ids[0].location_dest_id # destination_location = 67
                        internal_transfer_pick = self.env['stock.picking'].create({
                            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                            'location_id': source_location.id,
                            'location_dest_id': destination_location.id,
                            'origin': self.production_id.name,
                            'move_lines': [(0, 0, {
                                'name': self.production_id.name,
                                'product_id': pl.move_id.product_id.id,
                                'product_uom_qty': 1,
                                'product_uom': pl.move_id.product_uom.id,
                                'location_id':  destination_location.id,
                                'location_dest_id': source_location.id,
                            })],
                        })
                        immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, internal_transfer_pick.id)]})
                        internal_transfer_pick.action_assign()
                        internal_transfer_pick.move_ids_without_package.move_line_ids.update({'lot_id': current_lot_move_line.lot_id.id})
                        immediate_transfer.process()
                    else:
                        move = self.move_raw_ids.filtered(lambda m: m.id == pl.move_id.id and m.state not in ('done', 'cancel'))
                        qty_to_consume = float_round(self.qty_producing * move.unit_factor, precision_rounding=move.product_uom.rounding)
# 
                        move_lines = self.env['stock.move.line'].search([
                            ('id','in', move.move_line_ids.ids),
                            ('product_id', '=', move.product_id.id),
                            ('reference', '=', self.production_id.name),
                            ('location_dest_id','!=', move.product_id.property_stock_production.id),
                            ('state', '=', 'assigned'),
                        ])
                        
                        if move.product_id.tracking == 'lot':
                            move.move_line_ids.update({'lot_id':pl.lot_id.id,'qty_done': qty_to_consume})
                        else:
                            move.move_line_ids.update({'qty_done': qty_to_consume})
#                             
                        # Remove Reserved Quant For WH/Stock
                        stock_quant_id = self.env['stock.quant'].search([
                            ('product_id', '=', move.product_id.id),
                            ('location_id', '=', self.production_id.location_src_id.id),
                            ('reserved_quantity', '>', 0.0)
                        ])
# 
                        if stock_quant_id:
                            stock_quant_id.sudo().update({'reserved_quantity': 0.0})
                        for line in move_lines:
                            source_location = line.location_id
                            destination_location = line.location_dest_id
                            internal_transfer_pick = self.env['stock.picking'].create({
                                'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                                'location_id': source_location.id,
                                'location_dest_id': destination_location.id,
                                'origin': self.production_id.name,
                                'move_lines': [(0, 0, {
                                    'name': self.production_id.name,
                                    'product_id': move.product_id.id,
                                    'product_uom_qty': qty_to_consume,
                                    'product_uom': move.product_uom.id,
                                    'location_id':  destination_location.id,
                                    'location_dest_id': source_location.id,
                                    'picking_move_production_id':self.production_id.id
                                    })],
                                })
                             
                             
                            immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, internal_transfer_pick.id)]})
                            internal_transfer_pick.action_assign()
 
                            #Updates the lot_id which is selected on the wizard.
                            if move.product_id.tracking == 'lot':
                                internal_transfer_pick.move_ids_without_package.move_line_ids.update({'lot_id':pl.lot_id.id})
                            immediate_transfer.process()
                
                #Create Quality check workorderlines from here
                if not self.production_id.workorder_ids.mapped('check_ids'):
                    self.production_id.workorder_ids._create_checks()
                    
                if self.product_id.tracking != 'none':
                    self.production_id.workorder_ids.filtered(lambda x: x.state != 'done')[0].finished_lot_id = self.finished_lot_id.id
                    
                start_date = self.production_id._get_start_date()
                from_date_set = False
                for workorder in self.production_id.workorder_ids.filtered(lambda x: x.state != 'done'):
                    workcenter = workorder.workcenter_id
                    wos = workorders.search([('workcenter_id', '=', workcenter.id), ('date_planned_finished', '<>', False),
                                            ('state', 'in', ('ready', 'pending', 'progress','done')),
                                            ('date_planned_finished', '>=', start_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT))], order='date_planned_start')
                    from_date = start_date
                    to_date = workcenter.resource_calendar_id.attendance_ids and workcenter.resource_calendar_id.plan_hours(workorder.duration_expected / 60.0, from_date, compute_leaves=True, resource=workcenter.resource_id)
                    if to_date:
                        if not from_date_set:
                            # planning 0 hours gives the start of the next attendance
                            from_date = workcenter.resource_calendar_id.plan_hours(0, from_date, compute_leaves=True, resource=workcenter.resource_id)
                            from_date_set = True
                    else:
                        to_date = from_date + relativedelta(minutes=workorder.duration_expected)
                    # Check interval
                    for wo in wos:
                        if from_date < fields.Datetime.from_string(wo.date_planned_finished) and (to_date > fields.Datetime.from_string(wo.date_planned_start)):
                            from_date = fields.Datetime.from_string(wo.date_planned_finished)
                            to_date = workcenter.resource_calendar_id.attendance_ids and workcenter.resource_calendar_id.plan_hours(workorder.duration_expected / 60.0, from_date, compute_leaves=True, resource=workcenter.resource_id)
                            if not to_date:
                                to_date = from_date + relativedelta(minutes=workorder.duration_expected)
                    workorder.write({'date_planned_start': from_date, 'date_planned_finished': to_date})
                    if (workorder.operation_id.batch == 'no') or (workorder.operation_id.batch_size >= workorder.qty_production):
                        start_date = to_date
                    else:
                        qty = min(workorder.operation_id.batch_size, workorder.qty_production)
                        cycle_number = math.ceil(qty / workoself.production_id.product_qty / workcenter.capacity)
                        duration = workcenter.time_start + cycle_number * workorder.operation_id.time_cycle * 100.0 / workcenter.time_efficiency
                        to_date = workcenter.resource_calendar_id.attendance_ids and workcenter.resource_calendar_id.plan_hours(duration / 60.0, from_date, compute_leaves=True, resource=workcenter.resource_id)
                        if not to_date:
                            start_date = from_date + relativedelta(minutes=duration)
                
# 
#         return True

