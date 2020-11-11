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


from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_round


class MrpProductionInternalTransfer(models.TransientModel):
    _name = 'mrp.production.internal.transfer'
    _description = 'Manage Stock'

    @api.model
    def default_get(self, fields):
        res = super(MrpProductionInternalTransfer, self).default_get(fields)
        if self._context and self._context.get('active_id'):
            workorder = self.env['mrp.workorder'].browse(self._context['active_id'])
            todo_uom = workorder.product_uom_id.id
            if workorder.qty_producing:
                todo_quantity = workorder.qty_producing
            else:
                todo_quantity = workorder.qty_produced
            if 'workorder_id' in fields:
                res['workorder_id'] = workorder.id
            if 'production_id' in fields:
                res['production_id'] = workorder.production_id.id
            if 'product_id' in fields:
                res['product_id'] = workorder.product_id.id
            if 'product_uom_id' in fields:
                res['product_uom_id'] = todo_uom
            if 'product_qty' in fields:
                res['product_qty'] = todo_quantity
        return res

    production_id = fields.Many2one('mrp.production', 'Production')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    workorder_id = fields.Many2one('mrp.workorder', 'Workorder')
    produce_line_ids = fields.One2many('mrp.product.internal.transfer.line', 'product_internal_id', string='Product to Track')


    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        lines = []
        qty_todo = self.product_uom_id._compute_quantity(self.product_qty, self.workorder_id.product_uom_id, round=False)
        for move in self.production_id.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.bom_line_id):
            qty_to_consume = float_round(qty_todo * move.unit_factor, precision_rounding=move.product_uom.rounding)
            move_lines_do = self.env['stock.move.line'].search([('id','in', move.move_line_ids.ids),
                                                                ('product_id', '=', move.product_id.id), 
                                                                ('reference', '=', self.production_id.name),
                                                                ('state', 'in', ['assigned','done'])],
                                                                order='id desc', limit=1)
            for line in move_lines_do:
                source_location_src_id = line.location_dest_id

            # Workcenter Related Stock Move Line
            move_line_ids_do = self.env['stock.move.line'].\
                                        search([('id','in', move.move_line_ids.ids),
                                                ('workcenter_id','=', self.workorder_id.workcenter_id.id)])
             # Fetch Product On hand Quant For Scrap Effect
            if move.product_id.tracking == 'none':
            
                if move_line_ids_do:
                    on_hand_stock_quant_id = self.env['stock.quant'].\
                            search([('location_id', '=', move_line_ids_do.location_id.id),
                                    ('product_id', '=', move.product_id.id),
                                    ])
                else:
                    on_hand_stock_quant_id = self.env['stock.quant'].\
                            search([('location_id', '=', source_location_src_id.id),
                                    ('product_id', '=', move.product_id.id),
                                    ])
            else:
                if move_line_ids_do:
                   
                    on_hand_stock_quant_id = self.env['stock.quant'].\
                            search([('location_id', '=', move_line_ids_do.location_id.id),
                                    ('product_id', '=', move.product_id.id),
                                    ('lot_id','=',move.move_line_ids[0].lot_id.id)
                                    ])
                    #For Lot total quantity on hand purpose
                    on_hand_stock_quant_id_for_check = self.env['stock.quant'].\
                            search([('location_id', '=', move_line_ids_do.location_id.id),
                                    ('product_id', '=', move.product_id.id),
                                    ])
                # For getting  stock quant based on different lot
                elif not self.workorder_id.next_work_order_id and move.product_id.tracking == 'lot':
                    on_hand_stock_quant_id= self.env['stock.quant'].\
                            search([('location_id', '=', self.workcenter_id.work_location_id.id),
                                    ('product_id', '=', move.product_id.id),
                                    ('lot_id','=',move.move_line_ids[0].lot_id.id)
                                    ])
                            
                    #For Lot total quantity on hand purpose
                    on_hand_stock_quant_id_for_check = self.env['stock.quant'].\
                            search([('location_id', '=', self.workcenter_id.work_location_id.id),
                                    ('product_id', '=', move_do.product_id.id),
                                    ])
                else:
                    on_hand_stock_quant_id = self.env['stock.quant'].\
                            search([('location_id', '=', source_location_src_id.id),
                                    ('product_id', '=', move.product_id.id),
                                    ('lot_id','=',move.move_line_ids[0].lot_id.id)
                                    ])
                    #For Lot total quantity on hand purpose
                    on_hand_stock_quant_id_for_check = self.env['stock.quant'].\
                            search([('location_id', '=', source_location_src_id.id),
                                    ('product_id', '=', move.product_id.id),
                                    ])
           
            on_hand_stock_quant_val = 0
            
            #For Lot total quantity on hand purpose
            on_hand_stock_quant_val_for_check = 0
            
            if on_hand_stock_quant_id:
                for st_id in on_hand_stock_quant_id:
                    on_hand_stock_quant_val += st_id.quantity
            
            #serial + lot
            if move.product_id.tracking != 'none':
                if on_hand_stock_quant_id_for_check:
                    for st_check_id in on_hand_stock_quant_id_for_check:
                        on_hand_stock_quant_val_for_check += st_check_id.quantity
                        
            stock_moves_raws_ids = self.production_id.move_raw_ids.filtered(lambda x: x.product_id == move.product_id and x.state != 'done')
            # Repetition Fetch Product
            if len(stock_moves_raws_ids.ids) > 1:
                stock_moves_raws_len = len(stock_moves_raws_ids.ids)
                if move.product_id.tracking != 'none':
                    qty_reserved_calc = int(on_hand_stock_quant_val_for_check / stock_moves_raws_len)
                else:
                    qty_reserved_calc = int(on_hand_stock_quant_val / stock_moves_raws_len)
            else:
                if move.product_id.tracking != 'none':
                    qty_reserved_calc = int(on_hand_stock_quant_val_for_check)
                else:
                    qty_reserved_calc = int(on_hand_stock_quant_val)

            
            # Compare Product On Hand Qty And Product Qty
            qty_done_calc = qty_to_consume - int(qty_reserved_calc)
            if qty_done_calc > 0.0:
                qty_done_calc = qty_done_calc
            else:
                qty_done_calc = 0.0
            
            # Fetch Stock Move Line Location Base On Work Center
            work_move_lines = self.env['stock.move.line'].search([('id','in', move.move_line_ids.ids),
                                                             ('product_id', '=', move.product_id.id),
                                                             ('reference', '=', self.production_id.name),
                                                             ('workcenter_id','=', self.workorder_id.workcenter_id.id),
                                                             ('location_dest_id','!=', move.product_id.property_stock_production.id),
                                                             ])
            if work_move_lines:
                move_lines = work_move_lines
                for line in move_lines:
                    source_location = self.production_id.location_src_id
                    destination_location = line.location_id
            elif not self.workorder_id.next_work_order_id:
                source_location = self.production_id.location_src_id
                destination_location = self.workorder_id.workcenter_id.work_location_id
            else:
                # Fetch Stock Move Line Location Base On New Generated Record
                move_lines = move_lines_do
                for line in move_lines:
                    source_location = self.production_id.location_src_id
                    destination_location = line.location_dest_id

            if qty_done_calc > 0.0:
                lines.append({
                    'move_id': move.id,
                    'qty_to_consume': qty_to_consume,
                    'qty_done': qty_done_calc,
                    'product_uom_id': move.product_uom.id,
                    'product_id': move.product_id.id,
                    'qty_reserved': qty_reserved_calc,
                    'location_id': source_location.id,
                    'location_dest_id': destination_location.id,
                    'lot_id': move.move_line_ids[0].lot_id.id
                })
        self.produce_line_ids = [(0, 0, x) for x in lines]

    def do_produce(self):
        if self.produce_line_ids:
            produce_line = self.produce_line_ids[0]
            it_count_dup = 0
            lines = [(0, 0, line) for line in self.consumed_material_complete_trans_move_line_get_dup()]
            
            line_dup = [(0, 0, line) for line in self.consumed_material_complete_trans_move_line_get()]
            for p_line in lines:
                lines[it_count_dup][2].pop('lot_id')
                it_count_dup += 1
            
            internal_transfer_pick = self.env['stock.picking'].create({
                'picking_type_id': self.env.ref('mrp_production_customize.picking_type_complete_int_transfer').id,
                'location_id': produce_line.location_id.id,
                'location_dest_id': produce_line.location_dest_id.id,
                'origin': self.production_id.name,
                'workorder_id': self.workorder_id.id,
                'move_lines': lines,
                })
            internal_transfer_pick.action_assign()
            it_count = 0
            for itpm_id in internal_transfer_pick.move_ids_without_package:
                if itpm_id.product_id.tracking == 'lot':
                    itpm_id.move_line_ids.update({'lot_id':line_dup[it_count][2].get('lot_id')})
                    it_count +=1

    def do_complete_transfer(self):
        if self.produce_line_ids:
            produce_line = self.produce_line_ids[0]
            lines = [(0, 0, line) for line in self.consumed_material_complete_trans_move_line_get_dup()]
            
            line_dup = [(0, 0, line) for line in self.consumed_material_complete_trans_move_line_get()]
            internal_transfer_pick = self.env['stock.picking'].create({
                'picking_type_id': self.env.ref('mrp_production_customize.picking_type_complete_int_transfer').id,
                'location_id': produce_line.location_id.id,
                'location_dest_id': produce_line.location_dest_id.id,
                'origin': self.production_id.name,
                'workorder_id': self.workorder_id.id,
                'move_lines': lines,
                })
            internal_transfer_pick.action_assign()
            immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, internal_transfer_pick.id)]})
            it_count = 0
            for itpm_id in internal_transfer_pick.move_ids_without_package:
                if itpm_id.product_id.tracking in ['lot','serial']:
                    itpm_id.move_line_ids.update({'lot_id':line_dup[it_count][2].get('lot_id')})
                    it_count +=1
            
            immediate_transfer.process()

    def consumed_material_move_line_get(self):
        res = []
        for line in self.produce_line_ids:
            if line.qty_done > 0.0:
                move_line_dict = {
                    'name': self.production_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty_done,
                    'product_uom': line.product_uom_id.id,
                    'location_id':  line.location_dest_id.id,
                    'location_dest_id': line.location_id.id,
                    'lot_id':line.lot_id.id if  line.lot_id else False
                }
                res.append(move_line_dict)
        return res


    def consumed_material_complete_trans_move_line_get(self):
        res = []
        for line in self.produce_line_ids:
            if line.move_id.product_id.tracking == 'none':
                stock_quant_on_hand_id = self.env['stock.quant'].\
                                            search([('product_id', '=', line.product_id.id),
                                                    ('location_id', '=', line.location_id.id),
                                                    ])
            else:
                stock_quant_on_hand_id = self.env['stock.quant'].\
                                            search([('product_id', '=', line.product_id.id),
                                                    ('location_id', '=', line.location_id.id),
                                                    ('lot_id','=',line.lot_id.id)])
            if line.qty_done > stock_quant_on_hand_id.quantity:
                raise UserError('%s does not have enough stock for source location' % (str(line.product_id.name)))
            if line.qty_done > 0.0:
                move_line_dict = {
                    'name': self.production_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty_done,
                    'product_uom': line.product_uom_id.id,
                    'location_id':  line.location_dest_id.id,
                    'location_dest_id': line.location_id.id,
                    'lot_id':line.lot_id.id if  line.lot_id else False
                }
                res.append(move_line_dict)
        return res
    
    def consumed_material_complete_trans_move_line_get_dup(self):
        res = []
        for line in self.produce_line_ids:
            if line.move_id.product_id.tracking == 'none':
                stock_quant_on_hand_id = self.env['stock.quant'].\
                                            search([('product_id', '=', line.product_id.id),
                                                    ('location_id', '=', line.location_id.id),
                                                    ])
            else:
                stock_quant_on_hand_id = self.env['stock.quant'].\
                                            search([('product_id', '=', line.product_id.id),
                                                    ('location_id', '=', line.location_id.id),
                                                    ('lot_id','=',line.lot_id.id)])
            if line.qty_done > stock_quant_on_hand_id.quantity:
                raise UserError('%s does not have enough stock for source location' % (str(line.product_id.name)))
            if line.qty_done > 0.0:
                move_line_dict = {
                    'name': self.production_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty_done,
                    'product_uom': line.product_uom_id.id,
                    'location_id':  line.location_dest_id.id,
                    'location_dest_id': line.location_id.id,
                }
                res.append(move_line_dict)
        return res


class MrpProductInternalTransferLine(models.TransientModel):
    _name = "mrp.product.internal.transfer.line"
    _description = "Record Production Line"

    product_internal_id = fields.Many2one('mrp.production.internal.transfer')
    product_id = fields.Many2one('product.product', 'Product')
    qty_to_consume = fields.Float('To Consume', digits=dp.get_precision('Product Unit of Measure'))
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    qty_done = fields.Float('To Be Transferred', digits=dp.get_precision('Product Unit of Measure'))
    move_id = fields.Many2one('stock.move', 'Stock Move')
    qty_reserved = fields.Float('Reserved', digits=dp.get_precision('Product Unit of Measure'))
    location_id = fields.Many2one('stock.location', 'Source')
    location_dest_id = fields.Many2one('stock.location', 'Destination')
    lot_id = fields.Many2one('stock.production.lot','Lot/Serial No.')