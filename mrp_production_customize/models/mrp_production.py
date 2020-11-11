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

from collections import defaultdict
from odoo import api, fields, models, tools, _
from odoo.tools import float_compare, float_round
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import UserError, ValidationError


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    in_active = fields.Boolean(string="In Active", default=True)

    def open_produce_product(self):
        """
        Function to check if workorders are generated and open produce wizard
        :return:
        """
        self.ensure_one()
        if self.routing_id and not self.workorder_ids:
            raise UserError(_('Please create workorders first!'))
        if self.workorder_ids:
            if self.workorder_ids.filtered(lambda x:x.state != 'done' and x.qty_production_dup > 0):
                raise UserError(_('Please finish previous work orders to process remaining quantity!'))
        
        action = self.env.ref('mrp.act_mrp_product_produce').read()[0]
        return action

    def button_plan(self):
        for move in self.move_raw_ids:
            if move.reserved_availability < move.product_uom_qty or move.reserved_availability == 0.0:
                raise UserError('Quantity on hand of product %s is not sufficient.' %(str(move.product_id.name)))
        res = super(MrpProduction, self).button_plan()
        return res
    
    def _get_move_raw_values(self, bom_line, line_data):
        move = super(MrpProduction, self)._get_move_raw_values(bom_line, line_data)
        if not self.bom_id.routing_id:
            raise UserError(_('Please configure Route for Manufacture Order.'))
        operation_id = self.bom_id.routing_id.operation_ids[0]
        work_location = operation_id.workcenter_id.work_location_id
        if not work_location:
            raise UserError(_('Please configure Default Center Location for Work Center.'))
        move.update({'location_dest_id': work_location.id})
        self.in_active = True
        return move

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        work_center_cost = 0
        finished_move = self.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0 and x.location_dest_id == self.location_dest_id)
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                time_lines = work_order.time_ids.filtered(lambda x: x.date_end and not x.cost_already_recorded)
                duration = sum(time_lines.mapped('duration'))
                time_lines.write({'cost_already_recorded': True})
                work_center_cost += (duration / 60.0) * work_order.workcenter_id.costs_hour
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                qty_done = finished_move.product_uom._compute_quantity(finished_move.quantity_done, finished_move.product_id.uom_id)
                finished_move.price_unit = (sum([-m.value for m in consumed_moves]) + work_center_cost) / qty_done
                finished_move.value = sum([-m.value for m in consumed_moves]) + work_center_cost
        return True




    def button_mark_done(self):
        res = super(MrpProduction, self).button_mark_done()
        stock_quant_id_mo = self.env['stock.quant'].\
                            search([('product_id', '=', self.product_id.id),
                                    ('location_id', '=', self.product_id.property_stock_production.id)])
        if stock_quant_id_mo:
            total_onhand_val_mo = stock_quant_id_mo.quantity
            stock_quant_id_mo.sudo().update({'quantity': total_onhand_val_mo})
        stock_quant_on_hand_id_mo = self.env['stock.quant'].\
                            search([('product_id', '=', self.product_id.id),
                                    ('location_id', '=', self.location_dest_id.id)])
        if stock_quant_on_hand_id_mo:
            total_onhand_val_mo1 = stock_quant_on_hand_id_mo.quantity
            stock_quant_on_hand_id_mo.sudo().update({'quantity': total_onhand_val_mo1})

        for move in self.move_raw_ids:
            stock_quant_virtual_id_mo = self.env['stock.quant'].\
                                search([('product_id', '=', move.product_id.id),
                                        ('location_id', '=', move.product_id.property_stock_production.id)])
            if stock_quant_virtual_id_mo:
                for sqv_id in stock_quant_virtual_id_mo:
                    total_property_stock_production_mo = sqv_id.quantity
                    sqv_id.sudo().update({'quantity': total_property_stock_production_mo})

            stock_quant_on_hand_id_mo = self.env['stock.quant'].\
                                    search([('product_id', '=', move.product_id.id),
                                            ('location_id', '=', self.location_src_id.id)])
            if stock_quant_on_hand_id_mo:
                for sqoh_id in stock_quant_on_hand_id_mo:
                    total_location_src_stock_mo = sqoh_id.quantity
                    sqoh_id.sudo().update({'quantity': total_location_src_stock_mo})
        return res
    
    def post_inventory(self):
        for order in self:
            moves_not_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done')
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            for move in moves_to_do.filtered(lambda m: m.product_qty == 0.0 and m.quantity_done > 0):
                move.product_uom_qty = move.quantity_done
            # MRP do not merge move, catch the result of _action_done in order
            # to get extra moves.
            moves_to_do = moves_to_do._action_done()
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done') - moves_not_to_do
            order._cal_price(moves_to_do)
            moves_to_finish = order.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            
            if self.product_id.tracking == 'serial':
                moves_to_finish.move_line_ids.write({'state':'done'})
            else:
                moves_to_finish = moves_to_finish._action_done()
            order.workorder_ids.mapped('raw_workorder_line_ids').unlink()
            order.workorder_ids.mapped('finished_workorder_line_ids').unlink()
            order.action_assign()
            consume_move_lines = moves_to_do.mapped('move_line_ids')
            for moveline in moves_to_finish.mapped('move_line_ids'):
                if moveline.move_id.has_tracking != 'none' and moveline.product_id == order.product_id or moveline.lot_id in consume_move_lines.mapped('lot_produced_ids'):
#                     if any([not ml.lot_produced_ids and ml.qty_done > 0 for ml in consume_move_lines]):
#                         raise UserError(_('You can not consume without telling for which lot you consumed it'))
                    # Link all movelines in the consumed with same lot_produced_ids false or the correct lot_produced_ids
#                     filtered_lines = consume_move_lines.filtered(lambda ml: moveline.lot_id in ml.lot_produced_ids)
                    moveline.write({'consume_line_ids': [(6, 0, [x for x in consume_move_lines.ids])]})
                else:
                    # Link with everything
                    moveline.write({'consume_line_ids': [(6, 0, [x for x in consume_move_lines.ids])]})
                    
        return True

#    

#Method is inherited to stop the warning which is raised for Product in case of serial tracking.
class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center')
    is_updated = fields.Boolean()
    active=fields.Boolean( 'Active' ,default=True)
    is_moveline_used = fields.Boolean('Moveline Used',default=False)

    @api.constrains('product_uom_qty')
    def check_reserved_done_quantity(self):
        return True

class StockPicking(models.Model):
    _inherit = "stock.picking"

    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    move_id = fields.Many2one('stock.move', 'Stock Move')

class StockMove(models.Model):
    _inherit = "stock.move"

    original_move = fields.Boolean('Original Moves', default=True)
    has_reversed_quant = fields.Boolean('Has Reverse Quant',default=False)
    picking_move_production_id = fields.Many2one('mrp.production',string='Picking Move Reference')
 
    def _sanity_check_for_valuation(self):
        for move in self:
            # Apply restrictions on the stock move to be able to make
            # consistent accounting entries.
            if move._is_in() and move._is_out():
                raise UserError(_("The move lines are not in a consistent state: some are entering and other are leaving the company."))
            company_src = move.mapped('move_line_ids.location_id.company_id')
            company_dst = move.mapped('move_line_ids.location_dest_id.company_id')
            try:
                if company_src:
                    company_src.ensure_one()
                if company_dst:
                    company_dst.ensure_one()
            except ValueError:
                raise UserError(_("The move lines are not in a consistent states: they do not share the same origin or destination company."))
            if company_src and company_dst and company_src.id != company_dst.id:
                raise UserError(_("The move lines are not in a consistent states: they are doing an intercompany in a single step while they should go through the intercompany transit location."))
            move._create_in_svl()

    def _action_done(self, cancel_backorder=False):
        # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
        valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
        for move in self:
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move
                    continue
  
        # AVCO application
        valued_moves['in'].product_price_update_before_done()
  
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
  
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
        # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
        for valued_type in self._get_valued_types():
            todo_valued_moves = valued_moves[valued_type]
            if todo_valued_moves:
                todo_valued_moves._sanity_check_for_valuation()
                stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()
                continue
  
  
        for svl in stock_valuation_layers:
            if not svl.product_id.valuation == 'real_time':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
  
        stock_valuation_layers._check_company()
  
        # For every in move, run the vacuum for the linked product.
        products_to_vacuum = valued_moves['in'].mapped('product_id')
        company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[0] or self.env.company
        for product_to_vacuum in products_to_vacuum:
            product_to_vacuum._run_fifo_vacuum(company)
  
        return res

                
    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """
        self.ensure_one()
        active_model = self._context.get('active_model') if self._context.get('active_model') else ' '
        if active_model != 'mrp.production':
            
            if active_model == 'mrp.workorder':
                
                if not self._context.get('force_valuation_amount') and not self._context.get('forced_quantity'):
                    if self.product_id.type != 'product':
                    # no stock valuation for consumable products
                        return False
                    if self.restrict_partner_id:
                        # if the move isn't owned by the company, we don't make any valuation
                        return False
            
                    location_from = self.location_id
                    location_to = self.location_dest_id
                    company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
                    company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False
                    # Create Journal Entry for products arriving in the company; in case of routes making the link between several
                    # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
                    if self._is_in():
                        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
                        if location_from and location_from.usage == 'customer':  # goods returned from customer
                            self.with_context(force_company=company_to.id)._create_account_move_line(acc_dest, acc_valuation, journal_id)
                        else:
                            self.with_context(force_company=company_to.id)._create_account_move_line(acc_src, acc_valuation, journal_id)
            
                    # Create Journal Entry for products leaving the company
                    if self._is_out():
                        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
                        if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                            self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_src, journal_id)
                        else:
                            self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_dest, journal_id)
            
                    if self.company_id.anglo_saxon_accounting:
                        # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
                        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
                        if self._is_dropshipped():
                            self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_src, acc_dest, journal_id)
                        elif self._is_dropshipped_returned():
                            self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_dest, acc_src, journal_id)
            
                    if self.company_id.anglo_saxon_accounting:
                        #eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
                        self._get_related_invoices()._anglo_saxon_reconcile_valuation(product=self.product_id)
            else:
                if self.product_id.type != 'product':
                    # no stock valuation for consumable products
                    return False
                if self.restrict_partner_id:
                    # if the move isn't owned by the company, we don't make any valuation
                    return False

                location_from = self.location_id
                location_to = self.location_dest_id
                company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
                company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False

                # Create Journal Entry for products arriving in the company; in case of routes making the link between several
                # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
                if self._is_in():
                    journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
                    if location_from and location_from.usage == 'customer':  # goods returned from customer
                        self.with_context(force_company=company_to.id)._create_account_move_line(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost)
                    else:
                        self.with_context(force_company=company_to.id)._create_account_move_line(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost)

                # Create Journal Entry for products leaving the company
                if self._is_out():
                    cost = -1 * cost
                    journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
                    if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                        self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost)
                    else:
                        self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost)

                if self.company_id.anglo_saxon_accounting:
                    # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
                    journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
                    if self._is_dropshipped():
                        if cost > 0:
                            self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost)
                        else:
                            cost = -1 * cost
                            self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost)
                    elif self._is_dropshipped_returned():
                        if cost > 0:
                            self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost)
                        else:
                            cost = -1 * cost
                            self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost)

                if self.company_id.anglo_saxon_accounting:
                    #eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
                    self._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=self.product_id)


    @api.depends('move_line_ids.product_qty')
    def _compute_reserved_availability(self):
        res = super(StockMove, self)._compute_reserved_availability()
        """ Fill the `availability` field on a stock move, which is the actual reserved quantity
        and is represented by the aggregated `product_qty` on the linked move lines. If the move
        is force assigned, the value will be 0.
        """
        result = {data['move_id'][0]: data['product_qty'] for data in 
            self.env['stock.move.line'].read_group([('move_id', 'in', self.ids)], ['move_id','product_qty'], ['move_id'])}
        for rec in self:
            rec.reserved_availability = rec.product_id.uom_id._compute_quantity(result.get(rec.id, 0.0), rec.product_uom, rounding_method='HALF-UP') 
        return res

    @api.depends('move_line_ids.qty_done', 'move_line_ids.product_uom_id', 'move_line_nosuggest_ids.qty_done')
    def _quantity_done_compute(self):
        """ This field represents the sum of the move lines `qty_done`. It allows the user to know
        if there is still work to do.

        We take care of rounding this value at the general decimal precision and not the rounding
        of the move's UOM to make sure this value is really close to the real sum, because this
        field will be used in `_action_done` in order to know if the move will need a backorder or
        an extra move.
        """

        move_lines = self.env['stock.move.line']
        for move in self:
            move_lines |= move._get_move_lines()
  
        data = self.env['stock.move.line'].read_group(
            [('id', 'in', move_lines.ids)],
            ['move_id', 'product_uom_id', 'qty_done'], ['move_id', 'product_uom_id'],
            lazy=False
        )
        rec = defaultdict(list)
        for d in data:
            rec[d['move_id'][0]] += [(d['product_uom_id'][0], d['qty_done'])]
         
        quantity_done = 0
        for move in self:
            uom = move.product_uom
            if move.product_id.tracking == 'serial':
                quantity_done = sum(
                    self.env['uom.uom'].browse(line_uom_id)._compute_quantity(qty, uom, round=False)
                    for line_uom_id, qty in rec.get(move.id, [])
                )
                if quantity_done > move.product_uom_qty:
                    move.quantity_done = move.product_uom_qty
                else:
                    move.quantity_done = quantity_done
                     
            else:
                move.quantity_done = sum(
                    self.env['uom.uom'].browse(line_uom_id)._compute_quantity(qty, uom, round=False)
                    for line_uom_id, qty in rec.get(move.id, [])
                )

#         move_lines = self.env['stock.move.line']
#         for move in self:
#             move_lines |= move._get_move_lines()
#  
#         data = self.env['stock.move.line'].read_group(
#             [('id', 'in', move_lines.ids)],
#             ['move_id', 'product_uom_id', 'qty_done'], ['move_id', 'product_uom_id'],
#             lazy=False
#         )
#         print("\n\ndata===================",data)
#         
#         rec = defaultdict(list)
#         for d in data:
#             rec[d['move_id'][0]] += [(d['product_uom_id'][0], d['qty_done'])]
#         print("\n\nrec===================",rec)
#  
#         for move in self:
#             uom = move.product_uom
#             move.quantity_done = sum(
#                 self.env['uom.uom'].browse(line_uom_id)._compute_quantity(qty, uom, round=False)
#                 for line_uom_id, qty in rec.get(move.id, [])
#             )
#             print("\n\n33333333333333333333333333333",move.quantity_done)
                

        
class StockQuant(models.Model):
    _inherit = 'stock.quant'
 
    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
        """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. Typically, this method is called when reserving
        a move or updating a reserved move line. When reserving a chained move, the strict flag
        should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
        anything from the stock, so we disable the flag. When editing a move line, we naturally
        enable the flag, to reflect the reservation according to the edition.
 
        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            was done and how much the system was able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        reserved_quants = []
 
        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to reserve more products of %s than you have in stock.') % product_id.display_name)
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
#             if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
#                 raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.') % product_id.display_name)
        else:
            return reserved_quants
 
        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant
 
            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants
