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

class AccountLoanInstallment(models.Model):
    _name = 'account.loan.installment'
    _description = "Account Loan Installment"
    
    @api.multi
    @api.depends('due_principal','due_interest','due_fees')
    def calculate_installment_due(self):
        for line in self:
            line.installment_due = line.due_principal + line.due_interest + line.due_fees
            
    
        
    name = fields.Char('Description',size=64 )
    loan_id = fields.Many2one('account.loan', 'Loan')
    capital = fields.Float('Principal', digits=(12, 2),)
    interest = fields.Float('Interest', digits=(12, 2),)
    total = fields.Float('Installment', digits=(12, 2),)
    cheque_id = fields.Many2one('account.loan.bank.cheque','Bank Cheque')
    partner_id = fields.Many2one('res.partner','Customer')
    fees = fields.Float("Fees", digits=(12, 2),)
    date = fields.Date("Date")
    old_disburse_amt = fields.Float("Old Disburse Amount")
    is_paid_installment = fields.Boolean("Is paid")
    due_principal = fields.Float("Principal Due")
    due_interest = fields.Float("Interest Due")
    due_fees = fields.Float("Fee Due")
    installment_due = fields.Float("Installment Due",compute='calculate_installment_due')
    state = fields.Selection([
            ('draft','Draft'),
            ('open','Open'),
            ('paid','Paid'),
        ],'State', readonly=False, index=True, default='draft')
    outstanding_prin = fields.Float("Outstanding Principal", digits=(12, 2))
    outstanding_int = fields.Float("Outstanding Interest", digits=(12, 2))
    outstanding_fees = fields.Float("Outstanding Fees", digits=(12, 2))
    fee_lines = fields.One2many('fees.lines', 'installment_id', 'Fees Line')
    late_fee = fields.Float("Late Fee")
    
    local_principle = fields.Float('Local Principal', digits=(12, 2),default = 0.0)
    local_interest = fields.Float('Local Interest', digits=(12, 2),default = 0.0)
    local_fees = fields.Float("Local Fees", digits=(12, 2),default = 0.0)
    move_id = fields.Many2one('account.move', "Move")
    paid_prin = fields.Float('Paid Capital')
    paid_int = fields.Float('Paid Interest')
    paid_fees = fields.Float('Paid Fees')
    paid_fees_tx = fields.Float('Paid Fees Tax')
    paid_late_fee = fields.Float('Paid Late Fees')
    paid_late_fee_tx = fields.Float('Paid Late Fees Tax')
    
    
    @api.depends('outstanding_prin') 
    def onchange_principle(self):
        self.write({'local_principle':self.local_principle+self._context.get('prin')})
        
    @api.depends('outstanding_int') 
    def onchange_interest(self):
        self.write({'local_interest':self.local_interest+self._context.get('int')})
        
    @api.depends('outstanding_fees') 
    def onchange_fees(self):
        self.write({'local_fees':self.local_fees+self._context.get('fee')})
        
        
        
        
class loanInstallmentPeriod(models.Model):
    _name = 'loan.installment.period'
    _description = "Loan installment period"
    
    name = fields.Char('Period Name', size=64, required=True)
    period = fields.Integer('Loan Period(months)', required = True)
    
    
class PaymentScheduleLine(models.Model):
    
    _name = 'payment.schedule.line'
    _description = "payment schedule Lines"
    
    name = fields.Char('Description',size=64 )
    loan_id = fields.Many2one('account.loan', 'Loan')
    capital = fields.Float('Principal', digits=(12, 2),)
    interest = fields.Float('Interest', digits=(12, 2),)
    total = fields.Float('Installment', digits=(12, 2),)
    cheque_id = fields.Many2one('account.loan.bank.cheque','Bank Cheque')
    partner_id = fields.Many2one('res.partner','Customer')
    fees = fields.Float("Fees", digits=(12, 2),)
    date = fields.Date("Date")
    old_disburse_amt = fields.Float("Old Disburse Amount")
    is_paid_installment = fields.Boolean("Is paid")
    installment_id = fields.Many2many('account.loan.installment',string="Installment Line Id")
    
    
class Fees_lines(models.Model):
    _name  = 'fees.lines'
    _description = "Fees Lines"
    
    name = fields.Char("Type")
    product_id = fields.Many2one('product.product', "Product")
    base = fields.Float("Base")
    tax = fields.Float("Tax")
    base_paid = fields.Float("Base Paid")
    tax_paid = fields.Float("Tax Paid")
    installment_id = fields.Many2one('account.loan.installment', 'Installment Id')
    is_paid = fields.Boolean("Is Paid")
    
    
