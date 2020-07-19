#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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


import time
import datetime
# from openerp import pooler
# from openerp.osv import osv
from odoo import fields,models,api
from datetime import date
import math
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class account_loan_loantype(models.Model):
    _name = "account.loan.loantype"
    _description = "account loan type "
    
    name = fields.Char('Type Name', size=32,required=True)
#         'type':fields.selection(
#             [
#                 ('education','Education Loan'),('personal','Personal Loan'),
#                 ('vehicle','Vehicle Loan'),('home','Home Loan'),('business','Personal Loan'),
#             ],'Calculation Method',required=True),
    prooftypes = fields.One2many('account.loantype.prooflines', 'loan_type', 'Proof')
    loan_component_ids = fields.One2many('loan.component.line', 'loan_type_id', 'Component Line')
#     prooftypes = fields.Many2many('account.loan.proof.type', 'loantype_prooftype_rel', 'order_line_id', 'tax_id', 'Proof')
    calculation = fields.Selection(
        [
            ('flat','Flat'),
            ('reducing','Reducing'),
            ('cnt_prin','Constant Principal')
        ],'Calculation Method',required=True,default = 'reducing')
    interestversion_ids = fields.One2many('account.loan.loantype.interestversion','loantype_id','Interest Versions')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    account_id = fields.Many2one('account.account', string="Excess Payment Account")

#     _defaults = {
#         'calculation': lambda *a: 'reducing',
#     }
    
class account_loan_prooftypes(models.Model):
    _name = "account.loantype.prooflines"
    _description = "account loantype prooflines"
    
    name = fields.Many2one('account.loan.proof.type','Proof Type Name',size=64,required=True)
    shortcut = fields.Char("Shortcut",size=32)
    is_mandatory = fields.Boolean("Is Mandatory")
    loan_type = fields.Many2one('account.loan.loantype')
    
    @api.onchange('name')    
    def onchange_name(self):
        res = {'shortcut': self.name.shortcut}
        return {'value':res}
    
class account_loan_loantype_interestversion(models.Model):
    _name='account.loan.loantype.interestversion'
    _description = "account loan loantype interestversion"

    name = fields.Char('Name',size=32,required=True)
    loantype_id = fields.Many2one('account.loan.loantype','Loan Type')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    active = fields.Boolean('Active',default = True )
    interestversionline_ids = fields.One2many('account.loan.loantype.interestversionline','interestversion_id','Current Interest Version')
    sequence = fields.Integer('Sequence',size=32)

    _order = 'sequence'
    
#     _defaults = {
#         'active': lambda *a: True,
#     }

class account_loan_loantype_interestversionline(models.Model):
    _name='account.loan.loantype.interestversionline'
    _description = "account loan loantype interestversion line"
    
    name = fields.Char('Interest ID',size=32,required=True)
    interestversion_id = fields.Many2one('account.loan.loantype.interestversion','Loan Interest Id')
    min_month = fields.Integer('Minimum Month',size=32)
    max_month = fields.Integer('Maximum Month',size=32)
    min_amount = fields.Float('Minimum Amount', digits=(10,2))
    max_amount = fields.Float('Maximum Amount', digits=(10,2))
    rate = fields.Float('Rate',digits=(10,2))
    sequence = fields.Integer('Sequence',size=32)

    _order = 'sequence'
    
    
    
class LoanComponentLine(models.Model):
    
    _name = 'loan.component.line'
    _description = "loan component interestversion"
    
    product_id = fields.Many2one('product.product', string="Product")
    type = fields.Selection([('principal', 'Principal'), ('int_rate', 'Interest Rate'), ('fees','Fees'), ('late_fee','Late Fee')], string="Component Type")
    gl_code = fields.Many2one('account.account',string="GL Code")
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', index=True, required=True, default='fix', help="The computation method for the rule amount.")
    
#     amount_percentage_base = fields.Char(string='Percentage based on', help='result will be affected to a variable')
    amount_percentage_base = fields.Many2many('product.product', string='Percentage based on', help='result will be affected to a variable')
    quantity = fields.Float(default=1.0, string="Quantity")
    amount_percentage = fields.Float(string='Percentage (%)', digits=dp.get_precision('Product Unit of Measure'))
    amount_fix = fields.Float(string='Fixed Amount', digits=dp.get_precision('Product Price'))
    amount_python_compute = fields.Text(string='Python Code'
                                        )
    loan_type_id = fields.Many2one('account.loan.loantype')
    grace_period = fields.Integer("Grace Period(Month)")
    sequence = fields.Integer("Sequence")
    product_amt = fields.Float("Product Amount")
    tax_amount = fields.Float("Tax Amount")
    outstanding_product_amt = fields.Float('Outstanding Product Amt.')
    out_st = fields.Float("Outstanding")
    tenure = fields.Selection([('month', 'Month'), ('tenure', 'Loan Tenure'), ('per_year', 'Per Year')], "Fee Period",  default="month",)
    
    
    
    def _get_product_accounts(self):
        return {
            'income': self.product_id.property_account_income_id or self.product_id.categ_id.property_account_income_categ_id,
            'expense': self.product_id.property_account_expense_id or self.product_id.categ_id.property_account_expense_categ_id
        }
        
    @api.multi
    def _compute_tax_id(self):
        for line in self:
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id
            line.tax_id = taxes
            accounts = self._get_product_accounts()
            if accounts:
                line.gl_code = accounts['income']
        
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):

        result = {}
        self._compute_tax_id()
        return result
    
    @api.multi
    @api.onchange('amount_percentage_base')
    def product_id_onchange(self):
        res = []
        for o in self.loan_type_id.loan_component_ids:
            if self._origin.id != o.id:
                res.append(o.product_id.id)
        return {'domain':{'amount_percentage_base':[('id','in', res)]}}
    
    @api.one
    def _compute_rule(self):
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix, float(safe_eval(self.quantity)), 100.0
            except:
                raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
        elif self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base)),
                        float(safe_eval(self.quantity)),
                        self.amount_percentage)
            except:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).') % (self.name, self.code))
#         else:
#             try:
#                 safe_eval(self.amount_python_compute, {}, mode='exec', nocopy=True)
#                 return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
#             except:
#                 raise UserError(_('Wrong python code defined for salary rule %s (%s).') % (self.name, self.code))
     
