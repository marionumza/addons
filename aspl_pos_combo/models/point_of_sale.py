# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import models, fields, api, _
from datetime import timedelta
import pytz

from functools import partial


class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_combo = fields.Boolean('Enable Combo')
    edit_combo = fields.Boolean('Single Click for Edit Combo')
    hide_uom = fields.Boolean('Hide UOM')


class PosOrder(models.Model):
    _inherit="pos.order.line"

    in_combo = fields.Boolean('In combo',default=False)


class PosOrder(models.Model):
    _inherit="pos.order"

    def _order_fields(self,ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        new_order_line = []
        process_line = partial(self.env['pos.order.line']._order_line_fields)
        order_lines = [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False

        for order_line in order_lines:
            lp = order_line[2]['id']
            new_order_line.append(order_line)
            if 'combo_ext_line_info' in order_line[2]:
                own_pro_list = [process_line(l) for l in order_line[2]['combo_ext_line_info']] if order_line[2]['combo_ext_line_info'] else False
                if own_pro_list:
                    for own in own_pro_list:
                        print(own)
                        own[2]['in_combo'] = True
                        own[2]['price_unit'] = own[2]['unit_price']
                        own[2]['price_subtotal'] = 0
                        own[2]['price_subtotal_incl'] = 0
                        own[2]['tax_ids'] = [(6, 0, [])]
                        new_order_line.append(own)
        res.update({
            'lines': new_order_line,
        })
        return res

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_combo = fields.Boolean("Is Combo")
    product_combo_ids = fields.One2many('product.combo', 'product_tmpl_id')

class ProductCombo(models.Model):
    _name = 'product.combo'
    _description = 'Product Combo'
    
    product_tmpl_id = fields.Many2one('product.template') 
    require = fields.Boolean("Required", Help="Don't select it if you want to make it optional")
    pos_category_id = fields.Many2one('pos.category', "Categories")
    product_ids = fields.Many2many('product.product',string="Products")
    no_of_items = fields.Integer("No. of Items", default= 1)

    @api.onchange('require')
    def onchage_require(self):
        if self.require:
            self.pos_category_id = False

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args
        if self._context.get('is_required', False):
            args += [['available_in_pos', '=', True]]
        if self._context.get('category_from_line', False):
            pos_category_id = self.env['pos.category'].browse(self._context.get('category_from_line'))
            args += [['pos_categ_id', 'child_of', pos_category_id.id],['available_in_pos', '=', True]]
        return super(ProductProduct, self).name_search(name, args=args, operator='ilike', limit=100)

class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, configs=False):
        # res = super(ReportSaleDetails, self).get_sale_details()
        """ Serialise the orders of the day information
        params: date_start, date_stop string representing the datetime of order
        """
        if not configs:
            configs = self.env['pos.config'].search([])

        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
        today = today.astimezone(pytz.timezone('UTC'))
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            date_start = today

        if date_stop:
            # set time to 23:59:59
            date_stop = fields.Datetime.from_string(date_stop)
        else:
            # stop by default today 23:59:59
            date_stop = today + timedelta(days=1, seconds=-1)

        # avoid a date_stop smaller than date_start
        date_stop = max(date_stop, date_start)

        date_start = fields.Datetime.to_string(date_start)
        date_stop = fields.Datetime.to_string(date_stop)

        orders = self.env['pos.order'].search([
            ('date_order', '>=', date_start),
            ('date_order', '<=', date_stop),
            ('state', 'in', ['paid','invoiced','done']),
            ('config_id', 'in', configs.ids)])

        user_currency = self.env.user.company_id.currency_id

        total = 0.0
        products_sold = {}
        taxes = {}
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
            else:
                total += order.amount_total
            currency = order.session_id.currency_id

            for line in order.lines:
                if line.product_id.is_combo or line.product_id.list_price == 0:#remove product is commbo and product have price = 0
                    continue
                key = (line.product_id, line.price_unit, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount':0.0, 'base_amount':0.0})
                        taxes[tax['id']]['tax_amount'] += tax['amount']
                        taxes[tax['id']]['base_amount'] += tax['base']
                else:
                    taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount':0.0, 'base_amount':0.0})
                    taxes[0]['base_amount'] += line.price_subtotal_incl

        st_line_ids = self.env["account.bank.statement.line"].search([('pos_statement_id', 'in', orders.ids)]).ids
        if st_line_ids:
            self.env.cr.execute("""
                SELECT aj.name, sum(amount) total
                FROM account_bank_statement_line AS absl,
                     account_bank_statement AS abs,
                     account_journal AS aj 
                WHERE absl.statement_id = abs.id
                    AND abs.journal_id = aj.id 
                    AND absl.id IN %s 
                GROUP BY aj.name
            """, (tuple(st_line_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        return {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': payments,
            'company_name': self.env.user.company_id.name,
            'taxes': list(taxes.values()),
            'products': reversed(sorted([{
                'product_id': product.id,
                'product_display_name': product.display_name,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'discount': discount,
                'uom': product.uom_id.name,
                'is_combo': product.is_combo
            } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['quantity']))
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: