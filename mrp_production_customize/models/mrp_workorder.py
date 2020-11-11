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
from odoo.tools import float_compare, float_round
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    work_location_id = fields.Many2one('stock.location', string="Center Location", required=True)

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    qty_production_wo = fields.Float('Original Production Quantity Copy')
    qty_produced_copy = fields.Float(
        'Quantity Copy', default=0.0,
        readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="The number of products already handled by this work order")
    qty_production_dup = fields.Float('Stored Original Production Quantity')
    qty_remaining_wo = fields.Float('Quantity To Be Produced Copy',
                                    compute='_compute_qty_remaining',
                                    digits=dp.get_precision('Product Unit of Measure'))
    qty_producing_copy = fields.Float(
        'Currently Produced Quantity', default=1.0,
        digits=dp.get_precision('Product Unit of Measure'),
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    current_lot_move_line_id = fields.Many2one('stock.move.line',string='Current Lot Move Line')
    not_to_use = fields.Boolean(string='Not to use',default=False)

    @api.depends('qty_production_dup', 'qty_produced', 'qty_production_wo')
    def _compute_qty_remaining(self):
        for wo in self:
            wo.qty_remaining = float_round(wo.qty_production_wo - wo.qty_produced, precision_rounding=wo.production_id.product_uom_id.rounding)
            wo.qty_remaining_wo = float_round(wo.qty_production_dup - wo.qty_produced, precision_rounding=wo.production_id.product_uom_id.rounding)
    
    def _init_nextworkorder_states(self):
        self.next_work_order_id.state == 'pending'
        
    @api.depends('state', 'quality_state', 'current_quality_check_id', 'qty_producing','qty_producing_copy',
                 'component_tracking', 'test_type', 'component_id',
                 'move_finished_ids.state', 'move_finished_ids.product_id',
                 'move_raw_ids.state', 'move_raw_ids.product_id',
                 )    
    def _compute_component_data(self):
        self.component_remaining_qty = False
        self.component_uom_id = False
        for wo in self.filtered(lambda w: w.state not in ('done', 'cancel')):
            if wo.test_type in ('register_byproducts', 'register_consumed_materials') and wo.quality_state == 'none':
                move = wo.current_quality_check_id.workorder_line_id.move_id
                lines = wo._workorder_line_ids().filtered(lambda l: l.move_id == move)
                completed_lines = lines.filtered(lambda l: l.lot_id) if wo.component_id.tracking != 'none' else lines
                wo.component_remaining_qty = self._prepare_component_quantity(move, wo.qty_producing) - sum(completed_lines.mapped('qty_done'))
                wo.component_uom_id = lines[:1].product_uom_id
                
    

    def open_tablet_view(self):
        res = super(MrpWorkorder,self).open_tablet_view()
        self.ensure_one()
        
        if self.production_id.product_id.tracking == 'serial':
            self.qty_producing = 1.0
        stock_move = self.env['stock.move'].search([
                        ('state','=','assigned'),
                        ('product_id','=',self.component_id.id),
                        ('reference','=',self.production_id.name),
                        ('location_id','=',self.production_id.location_src_id.id),
                        ('location_dest_id','=',self.production_id.workorder_ids[0].workcenter_id.work_location_id.id)
                    ],limit=1)
#         print("Stock Move Lines===============",stock_move,self.component_id.name)
#         if stock_move:
#             self.lot_id = stock_move.move_line_ids[0].lot_id.id
        self.allow_producing_quantity_change = True
        for wo_line in self.raw_workorder_line_ids:
            if wo_line.move_id.product_id.tracking == 'serial' and wo_line.move_id.product_id == self.component_id:
                production_move = self.production_id.move_raw_ids.filtered(lambda w:w.id == wo_line.move_id.id)
                move_line = self.env['stock.move.line'].search([
                                ('id','in',production_move.move_line_ids.ids),
                                ('qty_done','>',0),
                                ('is_moveline_used','=',False)
                            ],order = 'id asc',limit=1)
                 
                if move_line:
                    self.lot_id = move_line.lot_id
                    self.current_lot_move_line_id = move_line
                    break
        return res
    
    @api.model
    def _prepare_component_quantity(self, move, qty_producing):
        """ helper that computes quantity to consume (or to create in case of byproduct)
        depending on the quantity producing and the move's unit factor"""
         
             
        if move.product_id.tracking == 'serial':
            uom = move.product_id.uom_id
            move_line = self.env['stock.move.line'].search([
                                ('id','in',move.move_line_ids.ids),
                                ('qty_done','>',0),
                                ('is_moveline_used','=',False)
                            ],order = 'id asc',limit=1)
                 
            if move_line:
                if self.current_lot_move_line_id:
                    self.current_lot_move_line_id.is_moveline_used = True
                self.lot_id = move_line.lot_id
                self.current_lot_move_line_id = move_line
                
        else:
            uom = move.product_uom
        return move.product_uom._compute_quantity(
            qty_producing * move.unit_factor,
            uom,
            round=False
        )
    
    def do_finish(self):
        res = super(MrpWorkorder, self).do_finish()
        if not self.next_work_order_id:
            work_order_ids = all([x.qty_remaining == 0.0 for x in self.production_id.workorder_ids])
            available_move_list = []
            current_lot_id = False
            if work_order_ids:
#                 print("\n\n\n")
#                 print("Work oRder ids================",work_order_ids)
                # Update Manufacture Product Virtual/Production Quant Before Total
                
                total_property_stock_production = 0
                total_location_src_stock = 0
                if self.production_id.product_id.tracking == 'none':
                    stock_quant_virtual_id_mo_before = self.env['stock.quant'].\
                                        search([('product_id', '=', self.production_id.product_id.id),
                                                ('location_id', '=', self.production_id.product_id.property_stock_production.id)])
                    total_property_stock_production = stock_quant_virtual_id_mo_before.quantity
                    
                    # Update Manufacture Product WH/Stock Quant Before Total
                    stock_quant_on_hand_id_mo_before = self.env['stock.quant'].\
                                            search([('product_id', '=', self.production_id.product_id.id),
                                                    ('location_id', '=', self.production_id.location_src_id.id)])
    #                 print("stock_quant_on_hand_id_mo_before============",stock_quant_on_hand_id_mo_before.quantity)
                    total_location_src_stock = stock_quant_on_hand_id_mo_before.quantity
                
                elif self.production_id.product_id.tracking == 'lot':  
                    finished_move_line_ids = self.production_id.finished_move_line_ids.filtered(lambda x: x.product_id.id == self.production_id.product_id.id and x.state != 'done')
                    
                    for finish_line in finished_move_line_ids:
                        current_lot_id = finish_line.lot_id.id
                        stock_quant_virtual_id_mo_before = self.env['stock.quant'].\
                                            search([('product_id', '=', self.production_id.product_id.id),
                                                    ('location_id', '=', self.production_id.product_id.property_stock_production.id),('lot_id','=',finish_line.lot_id.id)])                    
#                 print("Stock Virtual ids============",stock_quant_virtual_id_mo_before.quantity)
                        total_property_stock_production += stock_quant_virtual_id_mo_before.quantity
                        # Update Manufacture Product WH/Stock Quant Before Total
                        stock_quant_on_hand_id_mo_before = self.env['stock.quant'].\
                                                search([('product_id', '=', self.production_id.product_id.id),
                                                        ('location_id', '=', self.production_id.location_src_id.id),('lot_id','=',finish_line.lot_id.id)])
        #                 print("stock_quant_on_hand_id_mo_before============",stock_quant_on_hand_id_mo_before.quantity)
                        total_location_src_stock += stock_quant_on_hand_id_mo_before.quantity
                        
                elif self.production_id.product_id.tracking == 'serial':  
                    finished_move_line_ids = self.production_id.finished_move_line_ids.filtered(lambda x: x.product_id.id == self.production_id.product_id.id and x.state != 'done')
                    
                    for finish_line in finished_move_line_ids:
                        current_lot_id = finish_line.lot_id.id
                        stock_quant_virtual_id_mo_before = self.env['stock.quant'].\
                                            search([('product_id', '=', self.production_id.product_id.id),
                                                    ('location_id', '=', self.production_id.product_id.property_stock_production.id),('lot_id','=',finish_line.lot_id.id)])                    
#                 print("Stock Virtual ids============",stock_quant_virtual_id_mo_before.quantity)
                        total_property_stock_production = 1.0
                        # Update Manufacture Product WH/Stock Quant Before Total
                        stock_quant_on_hand_id_mo_before = self.env['stock.quant'].\
                                                search([('product_id', '=', self.production_id.product_id.id),
                                                        ('location_id', '=', self.production_id.location_src_id.id),('lot_id','=',finish_line.lot_id.id)])
        #                 print("stock_quant_on_hand_id_mo_before============",stock_quant_on_hand_id_mo_before.quantity)
                        total_location_src_stock = 1.0
                
#                 5/0
                # Consumed Materials Wh/Stock And Virtual/Production Calculation Before Partially Quantity
                for move in self.production_id.move_raw_ids:
                    stock_quant_virtual_id_cm_before = self.env['stock.quant'].\
                                        search([('product_id', '=', move.product_id.id),
                                                ('location_id', '=', move.product_id.property_stock_production.id)])
                    total_property_stock_production_cm = 0
                    for sqv_id in stock_quant_virtual_id_cm_before:
                        total_property_stock_production_cm += sqv_id.quantity
        
                # Assigned Move append in list
                for move in self.production_id.move_raw_ids.filtered(lambda x: x.state == 'assigned'):
                    available_move_list.append(move.id)
                        
                
                # Remaining Consumed Material Entry Created Code 
                self.production_id.with_context(active_model='mrp.production').post_inventory()
                
                for production in self.production_id.with_context(active_model='mrp.production'):
                    for move_raw in production.move_raw_ids:
                        move_raw.write({
                            'reference': production.name,  # set reference when MO name is different than 'New'
                        })
#                 print("After self.production_id.with_context==========")
                
                # Update Manufacture Product Virtual/Production Quant After Total
                if self.production_id.product_id.tracking == 'none':
                    stock_quant_virtual_id_mo_after = self.env['stock.quant'].\
                                        search([('product_id', '=', self.production_id.product_id.id),
                                                ('location_id', '=', self.production_id.product_id.property_stock_production.id)])
                    if stock_quant_virtual_id_mo_after and stock_quant_virtual_id_mo_before:
                        stock_quant_virtual_id_mo_after.sudo().update({'quantity': total_property_stock_production})
        
                    # Update Manufacture Product WH/Stock Quant After Total
                    stock_quant_on_hand_id_mo_after = self.env['stock.quant'].\
                                            search([('product_id', '=', self.production_id.product_id.id),
                                                    ('location_id', '=', self.production_id.location_src_id.id)])
                    if stock_quant_on_hand_id_mo_after and stock_quant_on_hand_id_mo_before:
                        stock_quant_on_hand_id_mo_after.sudo().update({'quantity': total_location_src_stock})
                        
                
                elif self.production_id.product_id.tracking == 'lot':
                    finished_move_line_ids = self.production_id.finished_move_line_ids.filtered(lambda x: x.product_id.id == self.production_id.product_id.id and x.state == 'done')
                    if finished_move_line_ids:
                        for finish_line in finished_move_line_ids:
                            if current_lot_id == finish_line.lot_id.id:
                                stock_quant_virtual_id_mo_after = self.env['stock.quant'].\
                                                search([('product_id', '=', self.production_id.product_id.id),
                                                        ('location_id', '=', self.production_id.product_id.property_stock_production.id),('lot_id','=',finish_line.lot_id.id)])
                                
                                if stock_quant_virtual_id_mo_after:
                                    stock_quant_virtual_id_mo_after.sudo().update({'quantity': total_property_stock_production})
                
                                # Update Manufacture Product WH/Stock Quant After Total
                                stock_quant_on_hand_id_mo_after = self.env['stock.quant'].\
                                                        search([('product_id', '=', self.production_id.product_id.id),
                                                                ('location_id', '=', self.production_id.location_src_id.id),('lot_id','=',finish_line.lot_id.id)])
                                if stock_quant_on_hand_id_mo_after:
                                    stock_quant_on_hand_id_mo_after.sudo().update({'quantity': total_location_src_stock})
                
                elif self.production_id.product_id.tracking == 'serial':
                    finished_move_line_ids = self.production_id.finished_move_line_ids.filtered(lambda x: x.product_id.id == self.production_id.product_id.id and x.state == 'done')
                    if finished_move_line_ids:
                        for finish_line in finished_move_line_ids:
                            if current_lot_id == finish_line.lot_id.id:
                                stock_quant_virtual_id_mo_after = self.env['stock.quant'].\
                                                search([('product_id', '=', self.production_id.product_id.id),
                                                        ('location_id', '=', self.production_id.product_id.property_stock_production.id),('lot_id','=',finish_line.lot_id.id)])
                                
                                if stock_quant_virtual_id_mo_after:
                                    stock_quant_virtual_id_mo_after.sudo().update({'quantity': 1.0})
                
                                # Update Manufacture Product WH/Stock Quant After Total
                                stock_quant_on_hand_id_mo_after = self.env['stock.quant'].\
                                                        search([('product_id', '=', self.production_id.product_id.id),
                                                                ('location_id', '=', self.production_id.location_src_id.id),('lot_id','=',finish_line.lot_id.id)])
                                if stock_quant_on_hand_id_mo_after:
                                    stock_quant_on_hand_id_mo_after.sudo().update({'quantity': 1.0})
                        
                
                #Inactive Duplication of Product Moves of Manufacturing product
                product_move_id=  self.env['stock.move.line'].\
                    search([('product_id', '=', self.product_id.id),
                    ('location_id','=',self.product_id.property_stock_production.id),
                    ('location_dest_id', '=', self.production_id.location_dest_id.id),
                    ('reference','!=',self.production_id.name)
                    ])
                        
                for move_line in product_move_id:
                    stock_pick_id = self.env['stock.picking'].search([('name','=',move_line.reference)])
                    if stock_pick_id:
                        if stock_pick_id.origin == self.production_id.name:
                            move_line.update({'active':False})
                        
                # Consumed Materials Wh/Stock And Virtual/Production Calculation Before Partially Quantity
                available_move_ids = self.env['stock.move'].search([('id','in', available_move_list)])
                        
                #Transfer extra quantity which is passed from source location
                if available_move_ids:
                    for move in available_move_ids:
                                 
                        #Update Stock Quantity Based on product for No-Tracking
                        if move.product_id.tracking == 'none':
                            qty_produced_consume = float_round(self.qty_produced * move.unit_factor, precision_rounding=move.product_uom.rounding)
                            stock_quant_virtual_id_cm_after = self.env['stock.quant'].\
                                                search([('product_id', '=', move.product_id.id),
                                                        ('location_id', '=', move.product_id.property_stock_production.id),
                                                        ('lot_id','=',False)])
                            if stock_quant_virtual_id_cm_after and stock_quant_virtual_id_cm_before:
                                stock_quant_virtual_id_cm_after.sudo().update({'quantity': total_property_stock_production_cm})
        # 
                            stock_quant_on_hand_id_cm_after = self.env['stock.quant'].\
                                                    search([('product_id', '=', move.product_id.id),
                                                            ('location_id', '=', self.production_id.location_src_id.id),
                                                            ('lot_id','=',False)])
                            for sqh_id in stock_quant_on_hand_id_cm_after:
                                    total_location_src_stock_cm = 0
                                    total_location_src_stock_cm = (sqh_id.quantity + qty_produced_consume)
#                                     print("Total Quantity----------",move.product_id.name,total_location_src_stock_cm)
                                    stock_quant_on_hand_id_cm_after.sudo().update({'quantity': total_location_src_stock_cm})    
                        #Update Stock Quantity Based on product for Lot(lot)
                        elif move.product_id.tracking == 'lot':
                            qty_produced_consume = float_round(self.qty_produced * move.unit_factor, precision_rounding=move.product_uom.rounding)
                            stock_quant_virtual_id_cm_after = self.env['stock.quant'].\
                                                search([('product_id', '=', move.product_id.id),
                                                        ('location_id', '=', move.product_id.property_stock_production.id),
                                                        ('lot_id','=',move.move_line_ids[0].lot_id.id)])
                            

                            if stock_quant_virtual_id_cm_after and stock_quant_virtual_id_cm_before:
                                stock_quant_virtual_id_cm_after.sudo().update({'quantity': total_property_stock_production_cm})
        # 
                            stock_quant_on_hand_id_cm_after = self.env['stock.quant'].\
                                                    search([('product_id', '=', move.product_id.id),
                                                            ('location_id', '=', self.production_id.location_src_id.id),
                                                            ('lot_id','=',move.move_line_ids[0].lot_id.id)])
                            for sqh_id in stock_quant_on_hand_id_cm_after:
                                    total_location_src_stock_cm = 0
                                    total_location_src_stock_cm = (sqh_id.quantity + qty_produced_consume)
#                                     print("Total Quantity----------",move.product_id.name,total_location_src_stock_cm)
                                    stock_quant_on_hand_id_cm_after.sudo().update({'quantity': total_location_src_stock_cm})    
                                 
                        #Update Stock Quantity Based on product for Serial(serial latest)
                        elif move.product_id.tracking == 'serial':
#                             print("Inside Serial===========")
                            qty_produced_consume = float_round(self.qty_produced * move.unit_factor, precision_rounding=move.product_uom.rounding)
                            stock_quant_virtual_id_cm_after = self.env['stock.quant'].\
                                                    search([('product_id', '=', move.product_id.id),
                                                            ('location_id', '=', move.product_id.property_stock_production.id)])
#                             if stock_quant_virtual_id_cm_after and stock_quant_virtual_id_cm_before:
#                                 stock_quant_virtual_id_cm_after.sudo().update({'quantity': total_property_stock_production_cm})
#                             print("After 1st for loop===========")
                            for line in move.move_line_ids:
                                stock_quant_on_hand_id_cm_after = self.env['stock.quant'].\
                                                        search([('product_id', '=', move.product_id.id),
                                                                ('location_id', '=', self.production_id.location_src_id.id),
                                                                ('lot_id','=',line.lot_id.id)])
                                if stock_quant_on_hand_id_cm_after:
                                    for sqh_id in stock_quant_on_hand_id_cm_after:
                                        total_location_src_stock_cm = 0
                                        total_location_src_stock_cm = (sqh_id.quantity + 1)
                                        sqh_id.sudo().update({'quantity': 0})
                                                     
                                                        
#                 5/0
#                 print("Before New Move==========")
                #After Post Inventory method extra stock_quants are added in Physical Locations-1.So we deduct its quantity.
                for new_move in self.production_id.move_raw_ids.filtered(lambda x: x.state == 'done' and not x.has_reversed_quant):
                    
                    
                    if new_move.product_id.tracking == 'none':
                        new_stock_quant = self.env['stock.quant'].sudo().search([
                                            ('product_id', '=', new_move.product_id.id),
                                            ('location_id', '=', new_move.location_dest_id.id),
                                            ('quantity','>=',new_move.quantity_done),
                                            ('lot_id','=',False),
                                           ],limit=1)
                    elif new_move.product_id.tracking == 'lot':
#                         print("Move Data==========",new_move.product_id.name,new_move.location_dest_id.name,new_move.move_line_ids[0].lot_id.name)
                        new_stock_quant = self.env['stock.quant'].sudo().search([
                                            ('product_id', '=', new_move.product_id.id),
                                            ('location_id', '=', new_move.location_dest_id.id),
                                            ('quantity','>=',new_move.quantity_done),
                                            ('lot_id','=',new_move.move_line_ids[0].lot_id.id)
                                           ],limit=1)
                    
                    elif new_move.product_id.tracking == 'serial':
#                         print("Move Data==========",new_move.product_id.name,new_move.location_dest_id.name,new_move.move_line_ids[0].lot_id.name)
                        
                        for new_line in new_move.move_line_ids:
                            new_stock_quant = self.env['stock.quant'].sudo().search([
                                                ('product_id', '=', new_move.product_id.id),
                                                ('location_id', '=', new_move.location_dest_id.id),
                                                ('quantity','=',1),
                                                ('lot_id','=',new_line.lot_id.id)
                                               ],limit=1)
                            if new_stock_quant:
                                new_stock_quant.sudo().update({'quantity':0})
                    
#                     print("New Stock Quant=========",new_stock_quant,new_stock_quant.quantity,new_move.quantity_done)
                    if new_stock_quant and new_move.product_id.tracking != 'serial':
                       new_stock_quant.sudo().update({'quantity':(new_stock_quant.quantity - new_move.quantity_done)}) 
#                     print("After write Stock quant=========",new_stock_quant.quantity)
#                     
                for new_move in self.production_id.move_raw_ids.filtered(lambda x: x.state == 'done' and not x.has_reversed_quant):
                    new_move.sudo().write({'has_reversed_quant':True})

                for new_move in self.production_id.move_raw_ids.filtered(lambda x: x.state != 'done'):
                    lot_list = []
#                     print('Move==============',new_move)
                    
                    if new_move.product_id.tracking == 'serial':
                        new_move_lines = self.env['stock.move.line'].sudo().search([('id','in',new_move.move_line_ids.ids)],order = 'id desc')
                        for new_m_line in new_move_lines:
#                             print("New M Lne========",new_m_line.id)
                            if new_m_line.lot_id.id in lot_list:
                                new_m_line.sudo().unlink()
                            else:
                                lot_list.append(new_m_line.lot_id.id)
                
        return res

    def action_open_manufacturing_order(self):
        action = self.do_finish()
        try:
            self.production_id.button_mark_done()
        except (UserError, ValidationError) as e:
            # log next activity on MO with error message
            self.env['mail.activity'].create({
                'res_id': self.production_id.id,
                'res_model_id': self.env['ir.model']._get(self.production_id._name).id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_warning').id,
                'summary': ('The %s could not be closed') % (self.production_id.name),
                'note': e.name,
                'user_id': self.env.user.id,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                'res_id': self.production_id.id,
                'target': 'main',
            }
        return action

    def _start_nextworkorder(self):
        rounding = self.product_id.uom_id.rounding
        if self.next_work_order_id.state == 'pending':
            self.next_work_order_id.state = 'ready'
            
            
    def _create_or_update_finished_line(self):
        """
        1. Check that the final lot and the quantity producing is valid regarding
            other workorders of this production
        2. Save final lot and quantity producing to suggest on next workorder
        """
        self.ensure_one()
        final_lot_quantity = self.qty_production
        rounding = self.product_uom_id.rounding
        # Get the max quantity possible for current lot in other workorders
        for workorder in (self.production_id.workorder_ids.filtered(lambda x:x.state != 'done') - self):
            # We add the remaining quantity to the produced quantity for the
            # current lot. For 5 finished products: if in the first wo it
            # creates 4 lot A and 1 lot B and in the second it create 3 lot A
            # and it remains 2 units to product, it could produce 5 lot A.
            # In this case we select 4 since it would conflict with the first
            # workorder otherwise.
            line = workorder.finished_workorder_line_ids.filtered(lambda line: line.lot_id == self.finished_lot_id)
            line_without_lot = workorder.finished_workorder_line_ids.filtered(lambda line: line.product_id == workorder.product_id and not line.lot_id)
            quantity_remaining = workorder.qty_remaining + line_without_lot.qty_done
            quantity = line.qty_done + quantity_remaining
            if line and float_compare(quantity, final_lot_quantity, precision_rounding=rounding) <= 0:
                final_lot_quantity = quantity
            elif float_compare(quantity_remaining, final_lot_quantity, precision_rounding=rounding) < 0:
                final_lot_quantity = quantity_remaining

        # final lot line for this lot on this workorder.
        current_lot_lines = self.finished_workorder_line_ids.filtered(lambda line: line.lot_id == self.finished_lot_id)
        # this lot has already been produced
#         if float_compare(final_lot_quantity, current_lot_lines.qty_done + self.qty_producing, precision_rounding=rounding) < 0:
#             raise UserError(_('You have produced %s %s of lot %s in the previous workorder. You are trying to produce %s in this one') %
#                 (final_lot_quantity, self.product_id.uom_id.name, self.finished_lot_id.name, current_lot_lines.qty_done + self.qty_producing))

        # Update workorder line that regiter final lot created
        if not current_lot_lines:
            current_lot_lines = self.env['mrp.workorder.line'].create({
                'finished_workorder_id': self.id,
                'product_id': self.product_id.id,
                'lot_id': self.finished_lot_id.id,
                'qty_done': self.qty_producing,
            })
        else:
            current_lot_lines.qty_done += self.qty_producing
            
    
            
            
    def record_production(self):
        if not self:
            return True
  
        self.ensure_one()
        self._check_company()
        #temporary change
#         self.allow_producing_quantity_change = True
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))
  
        # If last work order, then post lots used
        if not self.next_work_order_id:
            self._update_finished_move()
#   
        # Transfer quantities from temporary to final move line or make them final
#         self._update_moves()
        if self.product_id.tracking != 'none':
            workorder_lines_to_process = self._workorder_line_ids().filtered(lambda line: line.product_id != self.product_id and line.qty_done > 0)
            for line in workorder_lines_to_process:
                line._update_partial_move_lines()
#             5/0
        # # Transfer lot (if present) and quantity produced to a finished workorder line
        if self.product_tracking != 'none':
            self._create_or_update_finished_line()
#   
        # # Update workorder quantity produced
        self.qty_produced += self.qty_producing
        self.qty_produced_copy = self.qty_producing
   
        # # Suggest a finished lot on the next workorder
        if self.next_work_order_id and self.production_id.product_id.tracking != 'none' and not self.next_work_order_id.finished_lot_id:
            self.next_work_order_id._defaults_from_finished_workorder_line(self.finished_workorder_line_ids)
            # As we may have changed the quantity to produce on the next workorder,
            # make sure to update its wokorder lines
            self.next_work_order_id._apply_update_workorder_lines()
   
#         # # One a piece is produced, you can launch the next work order
        self._start_nextworkorder()
   
        # # Test if the production is done
        rounding = self.production_id.product_uom_id.rounding
        if float_compare(self.qty_produced, self.production_id.product_qty, precision_rounding=rounding) and float_compare(self.qty_produced, self.qty_production_dup, precision_rounding=rounding) < 0:
            previous_wo = self.env['mrp.workorder']
            if self.product_tracking != 'none':
                previous_wo = self.env['mrp.workorder'].search([
                    ('next_work_order_id', '=', self.id)
                ])
            candidate_found_in_previous_wo = False
            if previous_wo:
                candidate_found_in_previous_wo = self._defaults_from_finished_workorder_line(previous_wo.finished_workorder_line_ids)
            if not candidate_found_in_previous_wo:
                # self is the first workorder
                self.qty_producing = self.qty_remaining
#                 self.finished_lot_id = False
                if self.product_tracking == 'serial':
                    self.qty_producing = 1
# 
            self._apply_update_workorder_lines()
        else:
            self.qty_producing = 0
#             self.button_finish()
  
        # Update Previous Work Order
        if self.next_work_order_id:
            self.next_work_order_id.qty_production_wo = self.qty_produced
        # Do Finish Code
        if self.next_work_order_id:
            location_dest_id = self.next_work_order_id.workcenter_id.work_location_id
        else:
            location_dest_id = self.workcenter_id.work_location_id
        
        
        qty_todo_do = self.product_uom_id._compute_quantity(self.qty_produced, self.production_id.product_uom_id, round=False)
        qty_produced_do_copy = self.product_uom_id._compute_quantity(self.qty_produced_copy, self.production_id.product_uom_id, round=False)
        
#         print("Location Destination------",location_dest_id.name,self.next_work_order_id.workcenter_id.name)
#         print("Quantity to Do==========",qty_todo_do)
#         print("Quantity Produced Do Copy==========",qty_produced_do_copy)
        count = count1 = count2 = count3 = 1
#         print("Befor First FOr lopp=-===")
        for move_do in self.production_id.move_raw_ids.filtered(lambda x: x.state != 'done'):
            # Update Move Line
#             print("Move Do and move Do lines===========",move_do,move_do.move_line_ids)
#             move_do.move_line_ids.update({'done_move': True, 'state': 'done'})
            qty_produced_do_copy_consume = float_round(qty_produced_do_copy * move_do.unit_factor, precision_rounding=move_do.product_uom.rounding)
            qty_to_consume_do = float_round(qty_todo_do * move_do.unit_factor, precision_rounding=move_do.product_uom.rounding)
#             print("qty_produced_do_copy_consume==========",qty_produced_do_copy_consume)
#             print("qty_to_consume_do==========",qty_to_consume_do)
            
        
            move_lines_do = self.env['stock.move.line'].search([
                ('id','in', move_do.move_line_ids.ids),
                ('product_id', '=', move_do.product_id.id), 
                ('reference', '=', self.production_id.name),
                ('state', 'in', ['assigned','done'])], order='id desc', limit=1)
            
#             for line in move_lines_do:
#                 source_location_src_id = line.location_dest_id
            source_location_src_id = self.workcenter_id.work_location_id
             
#              
            move_line_product_uom_qty_do = move_do.move_line_ids[0].product_uom_qty
            to_consume_in_line_do = min(qty_to_consume_do, move_line_product_uom_qty_do)
#             print("move_line_product_uom_qty_do=====",move_line_product_uom_qty_do)
#             print("to_consume_in_line_do=====",to_consume_in_line_do)
            
#              
            move_line_ids_do = self.env['stock.move.line'].search([
                ('id','in', move_do.move_line_ids.ids),
                ('workcenter_id','=', self.workcenter_id.id)])
#             print("Move Lines Ids Do=========",move_line_ids_do)
#             move_line_ids_do.update({'done_move': True, 'state': 'done'})
            # Create moveline for internal transfer product in location
            move_line_id_ph1_ph2 = self.env['stock.move.line']. search([
                ('id','in', move_do.move_line_ids.ids),
                ('product_id', '=', move_do.product_id.id), 
                ('reference', '=', self.production_id.name),
                ('location_dest_id', '=', location_dest_id.id),
                ('location_dest_id','!=', move_do.product_id.property_stock_production.id)])
#             print("move_line_id_ph1_ph2",move_line_id_ph1_ph2)
            
            # Fetch Product On hand Quant For Scrap Effect
            if move_do.product_id.tracking == 'none':
                if move_line_ids_do:
                    on_hand_stock_quant_id = self.env['stock.quant'].\
                        search([('location_id', '=', move_line_ids_do.location_id.id),
                                ('product_id', '=', move_do.product_id.id)])
                # For getting  stock quant based on different lot
                elif not self.next_work_order_id and move_do.product_id.tracking == 'lot':
                    on_hand_stock_quant_id = self.env['stock.quant'].\
                        search([('location_id', '=', self.workcenter_id.work_location_id.id),
                                ('product_id', '=', move_do.product_id.id)])
                else:
                    on_hand_stock_quant_id = self.env['stock.quant'].\
                        search([('location_id', '=', source_location_src_id.id),
                                ('product_id', '=', move_do.product_id.id)])
#             print("On Hand Stock Quant Id======",move_do.product_id.name,on_hand_stock_quant_id)
            
            #serial latest
            elif move_do.product_id.tracking == 'serial':
                #Fetch Move lines
#                 move_check_lines = move_do.move_line_ids.filtered(lambda x: x.is_updated != True)
                move_check_lines = move_do.move_line_ids.filtered(lambda x:x.qty_done == 1.0)
#                 print("Move Check Lines========",move_do,move_check_lines)
#                  
                move_check_lines_lots = self.env['stock.production.lot']
#                  
                #Fetch Each Move line s Lot
                for mcl_id in move_do.move_line_ids.filtered(lambda x:x.qty_done == 1.0):
                    move_check_lines_lots |= mcl_id.lot_id
#                  
                if move_check_lines:
                    source_location_src_id = self.workcenter_id.work_location_id
                    on_hand_stock_quant_id = self.env['stock.quant'].search([
                        ('location_id', '=', source_location_src_id.id),
                        ('product_id', '=', move_do.product_id.id),
                        ('lot_id','in',move_check_lines_lots.ids),
                        ('quantity','>',0)],order = 'id asc' ,limit=qty_produced_do_copy*move_do.unit_factor)
#                      
                    #For Lot total quantity on hand purpose
                    on_hand_stock_quant_id_for_check = self.env['stock.quant'].search([
                        ('location_id', '=', source_location_src_id.id),
                        ('product_id', '=', move_do.product_id.id)])
#                      
                else:
                    on_hand_stock_quant_id = self.env['stock.quant'].search([
                        ('location_id', '=', source_location_src_id.id),
                        ('product_id', '=', move_do.product_id.id),
                        ('lot_id','=',move_do.move_line_ids[0].lot_id.id)])
                    #For Lot total quantity on hand purpose
                    on_hand_stock_quant_id_for_check = self.env['stock.quant'].search([
                        ('location_id', '=', source_location_src_id.id),
                        ('product_id', '=', move_do.product_id.id)])
#              
            else:
                if move_line_ids_do:
                    on_hand_stock_quant_id = self.env['stock.quant'].search([
                        ('location_id', '=', move_line_ids_do.location_id.id),
                        ('product_id', '=', move_do.product_id.id),
                        ('lot_id','=',move_do.move_line_ids[0].lot_id.id)])
                    #For Lot total quantity on hand purpose
                    on_hand_stock_quant_id_for_check = self.env['stock.quant'].search([
                        ('location_id', '=', move_line_ids_do.location_id.id),
                        ('product_id', '=', move_do.product_id.id)])
                # For getting  stock quant based on different lot
                elif not self.next_work_order_id and move_do.product_id.tracking == 'lot':
                    on_hand_stock_quant_id= self.env['stock.quant'].search([
                        ('location_id', '=', self.workcenter_id.work_location_id.id),
                        ('product_id', '=', move_do.product_id.id),
                        ('lot_id','=',move_do.move_line_ids[0].lot_id.id)
                    ])
                    #For Lot total quantity on hand purpose
                    on_hand_stock_quant_id_for_check = self.env['stock.quant'].search([
                        ('location_id', '=', self.workcenter_id.work_location_id.id),
                        ('product_id', '=', move_do.product_id.id)])
                else:
                    on_hand_stock_quant_id = self.env['stock.quant'].search([
                        ('location_id', '=', source_location_src_id.id),
                        ('product_id', '=', move_do.product_id.id),
                        ('lot_id','=',move_do.move_line_ids[0].lot_id.id)])
                    #For Lot total quantity on hand purpose
                    on_hand_stock_quant_id_for_check = self.env['stock.quant'].search([
                        ('location_id', '=', source_location_src_id.id),
                        ('product_id', '=', move_do.product_id.id)])
                    
            
#             print("On Hand Stock Quant Id======",move_do.product_id.name,on_hand_stock_quant_id,on_hand_stock_quant_id_for_check)
#              
            on_hand_stock_quant_val = 0
            #For Lot total quantity on hand purpose
            on_hand_stock_quant_val_for_check = 0
#              
            if on_hand_stock_quant_id:
                for st_id in on_hand_stock_quant_id:
                    on_hand_stock_quant_val += st_id.quantity
#             print("on_hand_stock_quant_val=========",on_hand_stock_quant_val)
             
            #serial + lot
            if move_do.product_id.tracking != 'none':
                if on_hand_stock_quant_id_for_check:
                    for st_check_id in on_hand_stock_quant_id_for_check:
                        on_hand_stock_quant_val_for_check += st_check_id.quantity
#            
            # Repetition Fetch Product
            stock_moves_raws_ids = self.production_id.move_raw_ids.filtered(lambda x: x.product_id == move_do.product_id and x.state != 'done')
           
            to_consume_qty_produced_do_cp_mul = 0.0
            for stock_m in stock_moves_raws_ids:
                to_consume_qty_produced_do_cp_mul += (qty_produced_do_copy * stock_m.unit_factor)
#             print("to_consume_qty_produced_do_cp_mul=====",to_consume_qty_produced_do_cp_mul)
            
            if move_do.product_id.tracking == 'none':
                if to_consume_qty_produced_do_cp_mul > on_hand_stock_quant_val:
                    raise UserError('Component product %s (Production Qty - %s -> Current On Hand Qty - %s ) does not have enough qty in order to fulfil current production, please update qty on hand or reduce your production qty.' %\
                                    (str(move_do.product_id.name), str(to_consume_qty_produced_do_cp_mul), str(on_hand_stock_quant_val)))
            # #serial + lot ID check:
            else:
                if to_consume_qty_produced_do_cp_mul > on_hand_stock_quant_val_for_check:
                    raise UserError('Component product %s (Production Qty - %s -> Current On Hand Qty - %s ) does not have enough qty in order to fulfil current production, please update qty on hand or reduce your production qty.' %\
                                    (str(move_do.product_id.name), str(to_consume_qty_produced_do_cp_mul), str(on_hand_stock_quant_val_for_check)))
#              
            #If Product Tracking is based on lot then lot_id is passed on move line else false is passed
            if not move_line_id_ph1_ph2 and move_do.product_id.tracking == 'lot' and self.next_work_order_id:
#                 print("Location Dest id============",location_dest_id   )
                stock_move_line_id = self.env['stock.move.line'].create({
                    'move_id': move_do.id,
                    'product_id': move_do.product_id.id,
                    'lot_id': move_do.move_line_ids[0].lot_id.id,
                    'product_uom_qty': move_line_product_uom_qty_do,
                    'product_uom_id': move_do.product_uom.id,
                    'qty_done': to_consume_in_line_do,
                    'workorder_id': self.id,
                    'workcenter_id': self.workcenter_id.id,
                    'done_move': False,
                    'reference': self.production_id.name,
                    'production_id': self.production_id.id,
                    'location_id': source_location_src_id.id,
                    'location_dest_id': location_dest_id.id,
                    })
#                 print("move L/ine Creatd----",stock_move_line_id)
#              
            #serial latest (Create Move Lines for each and every serial for Move product)
            elif move_do.product_id.tracking == 'serial' and self.next_work_order_id:
                lot_ids_to_pass = self.env['stock.production.lot']
                move_check_lines = move_do.move_line_ids.filtered(lambda x: x.is_updated != True)
#                  
                for stock_id in on_hand_stock_quant_id:
                    lot_ids_to_pass |= stock_id.lot_id
                
                
                move_check_lines = move_check_lines.filtered(lambda x:x.lot_id.id in lot_ids_to_pass.ids)
#                  
#                _id = self.env['stock.move.line'].create(vals)
#              
            elif not move_line_id_ph1_ph2 and move_do.product_id.tracking == 'none' and self.next_work_order_id:
#                 print("Inside If================",move_line_product_uom_qty_do,to_consume_in_line_do,source_location_src_id.name,location_dest_id.name)
                stock_move_line_id = self.env['stock.move.line'].create({
                    'move_id': move_do.id,
                    'product_id': move_do.product_id.id,
                    'lot_id': False,
                    'product_uom_qty': move_line_product_uom_qty_do,
                    'product_uom_id': move_do.product_uom.id,
                    'qty_done': to_consume_in_line_do,
                    'workorder_id': self.id,
                    'workcenter_id': self.workcenter_id.id,
                    'done_move': False,
                    'reference': self.production_id.name,
                    'production_id': self.production_id.id,
                    'location_id': source_location_src_id.id,
                    'location_dest_id': location_dest_id.id,
                    })
#                 print("move Line Creatd----",stock_move_line_id)
            elif move_line_id_ph1_ph2 and self.next_work_order_id:
#                 print("Inside Else")
                move_line_id_ph1_ph2.update({'qty_done': to_consume_in_line_do})
        # Record Production Code
        qty_produced_copy = self.product_uom_id._compute_quantity(self.qty_produced_copy, self.production_id.product_uom_id, round=False)
        qty_todo = self.product_uom_id._compute_quantity(self.qty_produced, self.production_id.product_uom_id, round=False)
#         print("\n\n")
        
#         print("Befor Second FOr lopp=-===")
        for move in self.production_id.move_raw_ids.filtered(lambda x: x.state != 'done'):
            qty_produced_copy_consume = float_round(qty_produced_copy * move.unit_factor, precision_rounding=move.product_uom.rounding)
            qty_to_consume = float_round(qty_todo * move.unit_factor, precision_rounding=move.product_uom.rounding)
            print("Second Move=========",qty_to_consume)
            
            move_line_product_uom_qty = move.move_line_ids[0].product_uom_qty
            to_consume_qty_produced_cp = min(qty_produced_copy_consume, move_line_product_uom_qty)
            to_consume_in_line = min(qty_to_consume, move_line_product_uom_qty)
            # Remove Reserve Quantity
            # Update Move Line
#             move.move_line_ids.update({'done_move': True, 'state': 'done'})
            stock_quant_id = self.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id),
                ('location_id', '=', self.production_id.location_src_id.id),
                ('reserved_quantity', '>', 0.0)])
#             print("Stock Quant Avaialble=======",stock_quant_id)
            
            if stock_quant_id:
                stock_quant_id.sudo().update({'reserved_quantity': 0.0})
#                 
#             move_line = self.env['stock.move.line'].search([
#                  ('qty_done','=',0.0),
#                  ('product_id', '=', move.product_id.id),
#                  ('reference', '=', self.production_id.name),
#                  ('workcenter_id','=', self.workcenter_id.id),
#                  ('location_dest_id','!=', move.product_id.property_stock_production.id)
#             ])
            #serial latest
            if move.product_id.tracking != 'serial':
                move_lines = self.env['stock.move.line'].search([
                    ('id','in', move.move_line_ids.ids),
                     ('product_id', '=', move.product_id.id),
                     ('reference', '=', self.production_id.name),
                     ('workcenter_id','=', self.workcenter_id.id),
                     ('location_dest_id','!=', move.product_id.property_stock_production.id)
                ])
                
                for line in move_lines:
                    #serial latest(#Fetch Source and destination location for internal transfer)
                    if move.product_id.tracking == 'serial':
                        source_location = self.workcenter_id.work_location_id
                        destination_location = location_dest_id
                    else:
                        source_location = line.location_id
                        destination_location = line.location_dest_id
                    
    #                 print("Source Location--------",source_location.name)
    #                 print("Desctination Location----",destination_location.name)
    #                 print("\n")
                    # Internal Transfer For Physical Locations-1  -> Physical Locations-2 
                    #                       Physical Locations-2  -> Physical Locations-3
                    internal_transfer_pick = self.env['stock.picking'].create({
                        'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                        'location_id': source_location.id,
                        'location_dest_id': destination_location.id,
                        'origin': self.production_id.name,
                        'move_lines': [(0, 0, {
                            'name': self.production_id.name,
                            'product_id': move.product_id.id,
                            'product_uom_qty': (self.qty_produced_copy * move.unit_factor),
                            'product_uom': move.product_uom.id,
                            'location_id':  destination_location.id,
                            'location_dest_id': source_location.id,
                            'picking_move_production_id':self.production_id.id
                        })]
                    })
                    count1 += 1
                    
    #                 
                    internal_transfer_pick.action_assign()
                    if move.product_id.tracking == 'lot':
                        internal_transfer_pick.move_ids_without_package.move_line_ids.update({'lot_id':move.move_line_ids[0].lot_id.id})
    #                  
                    #serial + lot
                    if move.product_id.tracking == 'serial':
                        internal_transfer_pick.move_ids_without_package.move_line_ids.update({'lot_id': line.lot_id.id})
                    
                    immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, internal_transfer_pick.id)]})
                    immediate_transfer.process()
                
#             print("Move Lines----------",move_lines)
            
#              
            #serial latest(Create Internal Transfer for each and every move line of move product)
            else:
                if self.next_work_order_id:
                    move_lines = move.move_line_ids.filtered(lambda x:x.qty_done == 1.0)
                    move_check_lines_lots = self.env['stock.production.lot']
                       
                    #Fetch Each Move line s Lot
                    for mcl_id in move.move_line_ids.filtered(lambda x:x.qty_done == 1.0):
                        move_check_lines_lots |= mcl_id.lot_id
                      
                      
                    on_hand_stock_quant_id_it = self.env['stock.quant'].search([
                            ('location_id', '=', source_location_src_id.id),
                            ('product_id', '=', move.product_id.id),
                            ('lot_id','in',move_check_lines_lots.ids),
                            ('quantity','>',0)],order = 'id asc' ,limit=qty_produced_do_copy*move.unit_factor)
                      
                    lot_ids_to_pass = self.env['stock.production.lot']
                      
                    for stock_internal in on_hand_stock_quant_id_it:
                        lot_ids_to_pass |= stock_internal.lot_id
                      
                    move_lines = move_lines.filtered(lambda x:x.lot_id.id in lot_ids_to_pass.ids)
                else:
                    move_lines = self.env['stock.move.line']
#              
                for line in move_lines:
                    #serial latest(#Fetch Source and destination location for internal transfer)
                    if move.product_id.tracking == 'serial':
                        source_location = self.workcenter_id.work_location_id
                        destination_location = location_dest_id
                    else:
                        source_location = line.location_id
                        destination_location = line.location_dest_id
                    
    #                 print("Source Location--------",source_location.name)
    #                 print("Desctination Location----",destination_location.name)
    #                 print("\n")
                    # Internal Transfer For Physical Locations-1  -> Physical Locations-2 
                    #                       Physical Locations-2  -> Physical Locations-3
                    internal_transfer_pick = self.env['stock.picking'].create({
                        'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                        'location_id': source_location.id,
                        'location_dest_id': destination_location.id,
                        'origin': self.production_id.name,
                        'move_lines': [(0, 0, {
                            'name': self.production_id.name,
                            'product_id': move.product_id.id,
                            'product_uom_qty': 1,
                            'product_uom': move.product_uom.id,
                            'location_id':  destination_location.id,
                            'location_dest_id': source_location.id,
                            'picking_move_production_id':self.production_id.id
                        })]
                    })
                    count1 += 1
                    
    #                 
                    internal_transfer_pick.action_assign()
                    if move.product_id.tracking == 'lot':
                        internal_transfer_pick.move_ids_without_package.move_line_ids.update({'lot_id':move.move_line_ids[0].lot_id.id})
    #                  
                    #serial + lot
                    if move.product_id.tracking == 'serial':
                        internal_transfer_pick.move_ids_without_package.move_line_ids.update({'lot_id': line.lot_id.id})
                    
                    immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, internal_transfer_pick.id)]})
                    immediate_transfer.process()
#             Stock Move Lines which are created for moves from above code are deleted as it is being added in main production move_raw_ids and extra quants becomes reserved and consumed. It is just used for domain purpose so we delete it after the use of this move lines in completed.
            if move.product_id.tracking != 'serial':
                move_lines.sudo().unlink()
            
            #serial + lot
            if not self.next_work_order_id:
                # Update Move Line
#                 move.move_line_ids.update({'done_move': True, 'state': 'done'})
                # Create Internal Transfer
                # Physical Locations-3 -> Virtual Locations/Production
#                  
                if move.product_id.tracking != 'serial':
                    physical_virtual_pick1 = self.env['stock.picking'].create({
                        'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                        'location_id': location_dest_id.id,
                        'location_dest_id': move.product_id.property_stock_production.id,
                        'origin': self.production_id.name,
                        'move_lines': [(0, 0, {
                            'name': self.production_id.name,
                            'product_id': move.product_id.id,
                            'product_uom_qty': (self.qty_produced_copy * move.unit_factor),
                            'product_uom': move.product_uom.id,
                            'location_id': location_dest_id.id,
                            'location_dest_id': move.product_id.property_stock_production.id,
                            'picking_move_production_id':self.production_id.id,
                            })]
                        })
                    immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, physical_virtual_pick1.id)]})
                    physical_virtual_pick1.action_assign()
                    #lot
                    if move.product_id.tracking == 'lot':
                        physical_virtual_pick1.move_ids_without_package.move_line_ids.update({'lot_id':move.move_line_ids[0].lot_id.id})
#                     5/0
                    immediate_transfer.process()
#                  
                #serial latest(Create Internal Transfer for Physical-3 -> Virtual/Production based on serial tracking
                else:
                    move_lines = move.move_line_ids.filtered(lambda x:x.qty_done == 1.0)
                    move_check_lines_lots = self.env['stock.production.lot']
#                  
                    #Fetch Each Move line s Lot
                    for mcl_id in move.move_line_ids.filtered(lambda x:x.qty_done == 1.0):
#                          
                        move_check_lines_lots |= mcl_id.lot_id
#                      
                    on_hand_stock_quant_id_it = self.env['stock.quant'].search([
                            ('location_id', '=', source_location_src_id.id),
                            ('product_id', '=', move.product_id.id),
                            ('lot_id','in',move_check_lines_lots.ids),
                            ('quantity','>',0)],order = 'id asc' ,limit=qty_produced_do_copy*move.unit_factor)
#                      
                    lot_ids_to_pass = self.env['stock.production.lot']
                    for stock_internal in on_hand_stock_quant_id_it:
                        lot_ids_to_pass |= stock_internal.lot_id
#                  
                    move_lines = move_lines.filtered(lambda x:x.lot_id.id in lot_ids_to_pass.ids)
#                      
                    for move_line in move_lines:
#                          
                        physical_virtual_pick1 = self.env['stock.picking'].create({
                            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                            'location_id': location_dest_id.id,
                            'location_dest_id': move.product_id.property_stock_production.id,
                            'origin': self.production_id.name,
                            'move_lines': [(0, 0, {
                                'name': self.production_id.name,
                                'product_id': move.product_id.id,
                                'product_uom_qty': to_consume_qty_produced_cp,
                                'product_uom': move.product_uom.id,
                                'location_id': location_dest_id.id,
                                'location_dest_id': move.product_id.property_stock_production.id,
                                'picking_move_production_id':self.production_id.id
                                })]
                            })
                        count2 += 1
                        immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, physical_virtual_pick1.id)]})
                        physical_virtual_pick1.action_assign()
#                          
                        #serial
                        physical_virtual_pick1.move_ids_without_package.move_line_ids.update({'lot_id': move_line.lot_id.id})
                        immediate_transfer.process()
#                         
#                         # Physical Locations-3 -> Virtual Locations/Production
#                         # Create Stock Move Line for serial tracking product
#                         stock_move_line =  self.env['stock.move.line'].create({
#                             'move_id': move.id,
#                             'product_id': move.product_id.id,
#                             'lot_id': move_line.lot_id.id,
#                             'product_uom_qty': move_line_product_uom_qty,
#                             'product_uom_id': move.product_uom.id,
#                             'qty_done': to_consume_qty_produced_cp,
#                             'workorder_id': self.id,
#                             'workcenter_id': self.workcenter_id.id,
#                             # 'done_wo': True,
#                             'done_move': True,
#                             'reference': self.production_id.name,
#                             'production_id': self.production_id.id,
#                             'location_id': location_dest_id.id,
#                             'location_dest_id': move.product_id.property_stock_production.id,
#                             'is_updated': True,
#                         })
#                         count3 += 1
#                         # move_line.update({'done_wo': False})
#                         stock_move_line.update({'state': 'done', 'done_move': True})
#                  
#                  
#                 # Physical Locations-3 -> Virtual Locations/Production
#                 # Stock Move Line
                move_line_ids = self.env['stock.move.line'].search([
                    ('id','in', move.move_line_ids.ids),
                    ('product_id', '=', move.product_id.id), 
                    ('location_dest_id', '=', move.product_id.property_stock_production.id),
                    ('state','in',['assigned','done']),
                    ('done_move','=', True)])
#                    
#                 #If Product Tracking is based on lot then lot_id is passed on move line else false is passed
#                 #serial + lot
#                 if not move_line_ids and move.product_id.tracking == 'lot':
#                     stock_move_line =  self.env['stock.move.line'].create({
#                         'move_id': move.id,
#                         'product_id': move.product_id.id,
#                         'lot_id': move.move_line_ids[0].lot_id.id,
#                         'product_uom_qty': move_line_product_uom_qty,
#                         'product_uom_id': move.product_uom.id,
#                         'qty_done': to_consume_qty_produced_cp,
#                         'workorder_id': self.id,
#                         'workcenter_id': self.workcenter_id.id,
#                         # 'done_wo': True,
#                         'done_move': True,
#                         'reference': self.production_id.name,
#                         'production_id': self.production_id.id,
#                         'location_id': location_dest_id.id,
#                         'location_dest_id': move.product_id.property_stock_production.id,
#                     })
#                     # move.move_line_ids.update({'done_wo': False})
#                     stock_move_line.update({'state': 'done', 'done_move': True})
#                   
#                 if not move_line_ids and move.product_id.tracking == 'none':
#                     stock_move_line =  self.env['stock.move.line'].create({
#                         'move_id': move.id,
#                         'product_id': move.product_id.id,
#                         'lot_id': False,
#                         'product_uom_qty': move_line_product_uom_qty,
#                         'product_uom_id': move.product_uom.id,
#                         'qty_done': to_consume_qty_produced_cp,
#                         'workorder_id': self.id,
#                         'workcenter_id': self.workcenter_id.id,
#                         # 'done_wo': True,
#                         'done_move': True,
#                         'reference': self.production_id.name,
#                         'production_id': self.production_id.id,
#                         'location_id': location_dest_id.id,
#                         'location_dest_id': move.product_id.property_stock_production.id,
#                     })
                    # move.move_line_ids.update({'done_wo': False})
#                     stock_move_line.update({'done_move': True})
#                   
#                 #serial latest
#                 elif move_line_ids and move.product_id.tracking != 'serial':
                    # move.move_line_ids.update({'done_wo': False})
#                     move_line_ids.update({'qty_done': to_consume_in_line,'done_move': True})
#           
        if not self.next_work_order_id:
            # Create Internal Transfer
            # Virtual Locations/Production -> Stock
            virtual_produ_pick1 = self.env['stock.picking'].create({
                'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                'location_id': self.production_id.product_id.property_stock_production.id,
                'location_dest_id': self.production_id.location_dest_id.id,
                'origin': self.production_id.name,
                'move_lines': [(0, 0, {
                    'name': self.production_id.name,
                    'product_id': self.production_id.product_id.id,
                    'product_uom_qty': qty_produced_copy,
                    'product_uom': self.production_id.product_uom_id.id,
                    'location_id': self.production_id.product_id.property_stock_production.id,
                    'location_dest_id': self.production_id.location_dest_id.id,
                    'picking_move_production_id':self.production_id.id
                    })]
                })
            immediate_transfer = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, virtual_produ_pick1.id)]})
            virtual_produ_pick1.action_assign()
            if self.production_id.product_id.tracking != 'none':
                virtual_produ_pick1.move_ids_without_package.move_line_ids.update({'lot_id': self.finished_lot_id.id})
            
            immediate_transfer.process()
#              
        self.qty_producing_copy = self.qty_producing
        self.qty_producing = 0
#          
        
        #New Code 25feb 2020
        if float_compare(self.qty_produced, self.qty_production, precision_rounding=rounding) >= 0:
            self.write({'not_to_use':True})
            self.button_finish()
  
        elif float_compare(self.qty_produced, self.qty_production_dup, precision_rounding=rounding) >= 0:
            self.write({'not_to_use':True})
            self.button_finish()
        return True
    
    
class MrpAbstractWorkorderLine(models.Model):
    _inherit = "mrp.workorder.line"  
    
    def _update_partial_move_lines(self):
        """ update a move line to save the workorder line data"""
        self.ensure_one()
        if self.lot_id:
            move_lines = self.move_id.move_line_ids.filtered(lambda ml: ml.lot_id == self.lot_id and not ml.lot_produced_ids)
        else:
            move_lines = self.move_id.move_line_ids.filtered(lambda ml: not ml.lot_id and not ml.lot_produced_ids)

        
        # Update reservation and quantity done
        for ml in move_lines:
            rounding = ml.product_uom_id.rounding
            if float_compare(self.qty_done, 0, precision_rounding=rounding) <= 0:
                break
            quantity_to_process = min(self.qty_done, ml.product_uom_qty - ml.qty_done)
            self.qty_done -= quantity_to_process

            new_quantity_done = ml.qty_done
            # if we produce less than the reserved quantity to produce the finished products
            # in different lots,
            # we create different component_move_lines to record which one was used
            # on which lot of finished product
            if float_compare(new_quantity_done, ml.product_uom_qty, precision_rounding=rounding) >= 0:
                ml.write({
                    'qty_done': new_quantity_done,
                    'lot_produced_ids': self._get_produced_lots(),
                })
            else:
                new_qty_reserved = ml.product_uom_qty - new_quantity_done
                default = {
                    'product_uom_qty': new_quantity_done,
                    'qty_done': new_quantity_done,
                    'lot_produced_ids': self._get_produced_lots(),
                }
                ml.copy(default=default)
                ml.with_context(bypass_reservation_update=True).write({
                    'product_uom_qty': new_qty_reserved,
                    'qty_done': 0
                })
