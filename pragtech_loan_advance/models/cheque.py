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
from odoo.exceptions import UserError, ValidationError, Warning 


class AccountLoanBankCheque(models.Model):
    _name='account.loan.bank.cheque'
    _description='Bank Account Cheque'
    _rec_name = 'code'
              
    loan_id = fields.Many2one('account.loan','Loan')
    code = fields.Char('Code', size=32, required=True)
    name = fields.Char('Name', size=32,required=True)
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    loan_bank_id = fields.Many2one('res.partner.bank','Bank', required=False)
    loan = fields.Float('Loan Amount', size=32)
    interest = fields.Float('Interest Amount', size=32)
    cheque_amount = fields.Float('Cheque Amount', size=32, required=True)
    account_id = fields.Many2one('account.account', 'General Account', required=True, index=True)
    state = fields.Selection([
            ('draft','Draft'),
            ('posted','Posted'),
            ('clear','Clear'),
            ('return','Return'),
            ('cancel','Cancel'),
            ('done','Done')
        ],'State', readonly=True, index=True, default='draft')
    date = fields.Date('Date', required=True, default=time.strftime('%Y-%m-%d'))
    clear_date = fields.Date('Cheque Clearing Date', required=False, readonly=True)
    return_date = fields.Date('Cheque Return Date', required=False, readonly=True)
    note = fields.Text('Notes')
    cheque_id = fields.One2many('account.loan.installment','cheque_id','Installments')
    voucher_id =  fields.Many2one('account.voucher', 'Voucher',readonly=True)
    fees = fields.Float("Fees")
    installment_id = fields.Many2one('account.loan.installment', "Installment Line Id")
    move_id = fields.Many2one('account.move', "Release Number")


    @api.onchange('partner_id')
    def onchange_bank_id(self):
        val={'loan_bank_id': False,'account_id':False,'loan_id':False}
        if not self.partner_id:
            return {'value':val}
        else:
            bank_ids=self.env['res.partner.bank'].search([('partner_id','=',self.partner_id.id)])
            loan_ids=self.env['account.loan'].search([('partner_id','=',self.partner_id.id)])
            obj=self.env['account.loan'].browse()
            bank_acc = obj.bank_acc.id
            if loan_ids.__len__()>0:
                val['loan_id']=loan_ids[0];
            if bank_ids.__len__()>0:
                acc_ids=self.env['res.partner.bank'].browse()
                for acc_id in acc_ids:
                    val['account_id']=acc_id.account_id.id;
               
                if acc_ids:
                    val['loan_bank_id']=bank_ids[0];
                    
                    return {'value':val}
                else:
                    val['loan_bank_id']=bank_ids[0];
                    return {'value':val}
            else:
                return {'value':val}
            
            
#     ## total calculatin of tax for fee calculation in installment ................
#     def get_tax_total(self, tx_ids, amount):
#         tax_amt = 0.0
#         for tx in tx_ids:
#             if not tx.price_include:
#                 print ('++++++++++++++++++++++++++++')
#                 tax = round((amount * tx.amount) / 100, 2)
#                 tax_amt = tax_amt + tax
#             else:
#                 tax = round(amount - ((amount * 100) / (100 + tx.amount)),2)
#                 tax_amt = tax_amt + tax
#                  
#         print (tax_amt,'=========================')
#         return tax_amt
    
    
    ## total calculatin of tax for fee calculation in installment ................
    def get_tax_total(self, tx_ids, amount):
        tax_amt = 0.0
        for tx in tx_ids:
            tax = round(amount - ((amount * 100) / (100 + tx.amount)),2)
            tax_amt = tax_amt + tax
        return tax_amt
    
            
    @api.multi
    def post_bank(self):
        ## call to create move_methods ......................
        move_id = self.create_moves()
        self.post()
        if move_id:
            self.write({'move_id':move_id.id,'state':'posted'})
            installment_records = self.env['account.loan.installment'].search([('cheque_id','=', self.id)])
#             for record in installment_records:
#                 record.write({'state':'paid'})
                
        for line in move_id.line_ids:
            self.loan_id.write({'move_id':[(4,line.id)]})
        
        payment_id = self.env['account.loan.repayment'].create({
            'name' : self.loan_id.partner_id.id,
            'pay_date' : datetime.datetime.now(),
            'amt' : self.cheque_amount,
            'loan_id' : self.loan_id.id,
            'release_number': move_id.id
            })
        self.loan_id.write({'repayment_details':[(4,payment_id.id)]})
        
        return True
    
    
    ##calculate taxes for non included .......................
    def get_interest_vals(self, tx_tot, account_id):
        if tx_tot:
            taxes_lines = {}
            taxes_lines.update({'partner_id':self.partner_id.id,'account_id':account_id.id, 'debit':0.0, 'credit':tx_tot})
            return taxes_lines
    
    def get_fees_vals(self, type_line):
        
        fees = {}
        if not type_line.gl_code:
            raise UserError('Please Configure GLCode For fees Amount')
        if self.loan_id.payment_freq == 'half_yearly' and type_line.product_amt:
            fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':type_line.product_amt*6})
        elif self.loan_id.payment_freq == 'yearly' and type_line.product_amt:
            fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':type_line.product_amt*12})
        elif self.loan_id.payment_freq == 'quarterly' and type_line.product_amt:
            fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':type_line.product_amt*3})
        else: 
            if type_line.product_amt:
                fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':type_line.product_amt})
        return fees
    
    
    
        
    def create_moves(self):
        ## accounting journal entries ..........................
        move_vals = {}
        name_des = "Loan Installment For: "
        date_new = date.today()
        move_lines_cr_capital = {}
        move_lines_cr_int = {}
        move_lines_dr = {}
        list_mv_line = []
        gl_code = False
        gl_code_int = False
        move_id = False
        interest_amt = self.interest
        interest_amt_tx = 0.0
        amount = 0.0
        amount_currency = False
        fees_amt = self.fees
        if not self.loan_id.company_id.currency_id:
            raise UserError('Please Define Company Currency')
        company_curren = self.loan_id.company_id.currency_id
        
        if not self.loan_id.journal_repayment_id.currency_id:
                raise UserError('Please Define Journal repayment Currency')
            
        currency_id = self.loan_id.journal_repayment_id.currency_id
        
        if self.loan_id and self.state not in ['posted','clear','cancel','done']:
            if not self.loan_id.journal_repayment_id:
                raise UserError('Please Configure Loan Disbursement Journal')
            
            if self.loan_id.loan_type:
                for type_line in self.loan_id.loan_type.loan_component_ids:
                    if type_line.type == 'principal':
                        if not type_line.gl_code:
                            raise UserError(_('Please Configure GLCode For Principal Amount'))
                        gl_code = type_line.gl_code.id
                    if type_line.type == 'int_rate':
                        if not type_line.gl_code:
                            raise UserError(_('Please Configure GLCode For Interest Amount'))
                        gl_code_int = type_line.gl_code.id
                        for tx_line in type_line.tax_id:
                            tx_tot = self.get_tax_total(tx_line, self.interest)
                            if tx_tot:
                                int_taxes = {}
                                interest_amt = interest_amt - tx_tot
                                if currency_id.id != company_curren.id:
                                    amount_currency = tx_tot
                                    amount = company_curren.with_context(date=date_new).compute(tx_tot, currency_id)
                                else:
                                    amount_currency = False
                                if not amount_currency:
                                    int_taxes.update({'partner_id':self.partner_id.id,'account_id':tx_line.account_id.id, 'debit':0.0, 'credit':tx_tot})
                                else:
                                    int_taxes.update({'partner_id':self.partner_id.id,'account_id':tx_line.account_id.id, 'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,'currency_id':currency_id.id})
                                list_mv_line.append((0, 0, int_taxes))
                        
                    if type_line.type == 'fees':
                        if not type_line.tax_id:
                            fees = {}
                            if currency_id.id != company_curren.id:
                                amount_currency = fees_amt
                                amount = company_curren.with_context(date=date_new).compute(fees_amt, currency_id)
                            else:
                                amount_currency = False
                            
                            if not type_line.gl_code:
                                raise UserError(_('Please Configure GLCode For fees Amount'))
                            if self.loan_id.payment_freq == 'half_yearly' and type_line.product_amt:
                                if not amount_currency:
                                    fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':fees_amt})
                                else:
                                    fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,'currency_id':currency_id.id })
                            elif self.loan_id.payment_freq == 'yearly' and type_line.product_amt:
                                if not amount_currency:
                                    fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':fees_amt})
                                else:
                                    fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,'currency_id':currency_id.id })
                                    
                            elif self.loan_id.payment_freq == 'quarterly' and type_line.product_amt:
                                if not amount_currency:
                                    fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':fees_amt})
                                else:
                                    fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,'currency_id':currency_id.id })
                                    
                            else: 
                                if type_line.product_amt:
                                    if not amount_currency:
                                        fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':fees_amt})
                                    else:
                                        fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,'currency_id':currency_id.id })
                            list_mv_line.append((0, 0, fees))
                        if type_line.tax_id:
#                             for tx_line in type_line.tax_id:
                            fees = {}
                            fees_dict = {}
                            interest_dict = {}
                            if not type_line.gl_code:
                                raise UserError(_('Please Configure GLCode For fees Amount'))
                            tx_tot = self.get_tax_total(type_line.tax_id, self.fees)
                            new_amt = round((self.fees - tx_tot),2)
                            
                            if currency_id.id != company_curren.id:
                                amount_currency = new_amt
                                amount = company_curren.with_context(date=date_new).compute(new_amt, currency_id)
                            else:
                                amount_currency = False
                            if not amount_currency:
                                fees_dict.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':new_amt})
                            else:
                                fees_dict.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0,\
                                                   'credit':amount, 'amount_currency':-amount_currency,'currency_id':currency_id.id})
                            
                            
                            if currency_id.id != company_curren.id and tx_tot:
                                amount_currency = tx_tot
                                amount = company_curren.with_context(date=date_new).compute(tx_tot, currency_id)
                            else:
                                amount_currency = False
                                
                            if not amount_currency:
                                interest_dict = self.get_interest_vals(tx_tot, type_line.tax_id.account_id)
                            else:
                                interest_dict.update({'partner_id':self.partner_id.id,'account_id':type_line.tax_id.account_id.id, 'debit':0.0, 'credit':amount, 'amount_currency':-amount_currency,'currency_id':currency_id.id})
#                             
                            if fees_dict:
                                list_mv_line.append((0, 0, fees_dict))
                            if interest_dict:
                                list_mv_line.append((0, 0, interest_dict))
                                    
            
            move_vals.update({'name':'/','ref':name_des + self.loan_id.loan_id,\
                              'date':date_new,'journal_id':self.loan_id.journal_repayment_id.id,\
                              })
            
            if not self.loan_id.journal_repayment_id.default_debit_account_id:
                raise UserError(_('Please Check Repayment Journal Default Debit Account'))
            
            
            if company_curren:
                if currency_id.id != company_curren.id:
                    amount_currency = self.cheque_amount
                    amount = company_curren.with_context(date=date_new).compute(self.cheque_amount, currency_id)
                else:
                    amount_currency = False
            if not amount_currency: 
                move_lines_dr.update({
                                'account_id':self.loan_id.journal_repayment_id.default_debit_account_id.id,
    #                             'name':name_des+ self.loan_id.loan_id,
                                'debit':self.cheque_amount,
                                'credit':0.0,
                                'partner_id':self.partner_id.id,
                                
                    })
            else:
                move_lines_dr.update({
                                'account_id':self.loan_id.journal_repayment_id.default_debit_account_id.id,
    #                             'name':name_des+ self.loan_id.loan_id,
                                'debit':amount,
                                'credit':0.0,
                                'partner_id':self.partner_id.id,
                                'amount_currency':amount_currency,
                                'currency_id':currency_id.id
                    })
                
            list_mv_line.append((0, 0, move_lines_dr))
            ##movelines for principal product .......................
            if company_curren:
                if currency_id.id != company_curren.id:
                    amount_currency = self.loan
                    amount = company_curren.with_context(date=date_new).compute(self.loan, currency_id)
                else:
                    amount_currency = False
            if not amount_currency:
                move_lines_cr_capital.update({
                                'account_id':gl_code,
    #                             'name':name_des+ self.loan_id.loan_id,
                                'credit':self.loan,
                                'debit':0.0,
                                'partner_id':self.partner_id.id,
                    })
            else:
                move_lines_cr_capital.update({
                                'account_id':gl_code,
    #                             'name':name_des+ self.loan_id.loan_id,
                                'credit':amount,
                                'debit':0.0,
                                'partner_id':self.partner_id.id,
                                'amount_currency':-amount_currency,
                                'currency_id':currency_id.id
                    })
                
            list_mv_line.append((0, 0, move_lines_cr_capital))
            ##movelines for interest product .......................
            if interest_amt:
                if company_curren:
                    if currency_id.id != company_curren.id:
                        amount_currency = interest_amt
                        amount = company_curren.with_context(date=date_new).compute(interest_amt, currency_id)
                    else:
                        amount_currency = False
                
                if not amount_currency:
                    move_lines_cr_int.update({
                                    'account_id':gl_code_int,
        #                             'name':name_des+ self.loan_id.loan_id,
                                    'credit':interest_amt,
                                    'debit':0.0,
                                    'partner_id':self.partner_id.id,
                                    
                        })
                else:
                    move_lines_cr_int.update({
                                    'account_id':gl_code_int,
        #                             'name':name_des+ self.loan_id.loan_id,
                                    'credit':amount,
                                    'debit':0.0,
                                    'partner_id':self.partner_id.id,
                                    'amount_currency':-amount_currency,
                                    'currency_id':currency_id.id
                        })
                    
            else:
                if company_curren:
                    if currency_id.id != company_curren.id:
                        amount_currency = self.interest
                        amount = company_curren.with_context(date=date_new).compute(self.interest, currency_id)
                    else:
                        amount_currency = False
                
                if not amount_currency:
                    move_lines_cr_int.update({
                                    'account_id':gl_code_int,
        #                             'name':name_des+ self.loan_id.loan_id,
                                    'credit':self.interest,
                                    'debit':0.0,
                                    'partner_id':self.partner_id.id,
                        })
                else:
                    move_lines_cr_int.update({
                                        'account_id':gl_code_int,
            #                             'name':name_des+ self.loan_id.loan_id,
                                        'credit':amount,
                                        'debit':0.0,
                                        'partner_id':self.partner_id.id,
                                        'amount_currency':-amount_currency,
                                        'currency_id':currency_id.id
                            })
                    
            list_mv_line.append((0, 0, move_lines_cr_int))
            print ('list_mv_line',list_mv_line)
            move_vals.update({'line_ids':list_mv_line})
            move_id = self.env['account.move'].create(move_vals)
            if move_id:
                move_id.post()
                return move_id
        
        
#     @api.multi
#     def post_bank(self):
#         res = False
#         def make_voucher(loan):
#             
#             ln_id = loan.loan_id
#             int_acc = ln_id.int_acc.id
#             cus_acc = ln_id.cus_pay_acc.id
#             
#             inv = {
#                 'name': loan.loan_id.loan_id,
#                 'voucher_type':'sale',
#                 'account_id': loan.account_id.id,
#                 'narration': loan.name,
#                 'date':loan.date,
#                 'partner_id':loan.partner_id.id,
#                 'loan_id':ln_id.id,
#             }
# 
#             inv_obj = self.env['account.voucher']
#             inv_id = inv_obj.create(inv)
#             inv_id2 = self.env['account.voucher.line'].create({
# #                 'partner_id':loan.partner_id.id,
#                 'name': loan.name,
#                 'price_unit':loan.loan,
#                 'account_id':cus_acc,
#                 'type':'cr',
#                 'voucher_id':inv_id.id,
#             })
#                     
#             inv_id1 = self.env['account.voucher.line'].create({
# #                 'partner_id':loan.partner_id.id,
#                 'name': loan.name,
#                 'price_unit':loan.interest,
#                 'account_id':int_acc,
#                 'type':'cr',
#                 'voucher_id':inv_id.id,
#             })
#             return inv_id
# 
#         for o in self:
#             res = make_voucher(o)
#             if res:
#                 if res.state == 'draft' or 'proforma':
#                     res.proforma_voucher()
#                     if res.move_id:
#                         for x in res.move_id.line_ids:
#                             x.write({'acc_loan_id':self.loan_id.id})
#                     self.write({'state':'posted'})
#                     self.write({'voucher_id': res.id})  
#         return res
    
    def cheque_cancel(self):
        self.write({'state':'cancel'})
        
    ##for return the cheque code ..................... 
    @api.multi
    def cheque_return(self):
        if self.move_id:
            date = datetime.date.today()
            context = {"active_ids": [self.move_id.id], "active_id": self.move_id.id}
            # Now I create invoice.
            move_reversal_id = self.env['account.move.reversal'].create({
                'date': date,
            })
            reverse_entry = move_reversal_id.with_context(context).reverse_moves()
            self.write({'state':'return', 'note':"Check Bounced"}) 
        return reverse_entry
    
        
        
#         self.write({'return_date': time.strftime('%Y-%m-%d')})
#         res = False
#         def make_voucher(loan):
#             print ('int returrrrrrrrrrrrrrrrrrrrrrrrrr')
#             ln_id = loan.loan_id
#             int_acc = ln_id.int_acc.id
#             cus_acc = ln_id.cus_pay_acc.id
#             
#             inv = {
#                 'name': loan.loan_id.loan_id,
#                 'voucher_type':'sale',
#                 'account_id': loan.loan_id.bank_acc.id,
#                 'narration': loan.name,
#                 'date':loan.date,
#                 'partner_id':loan.partner_id.id,
#             }
#             inv_obj = self.env['account.voucher']
#             inv_id = inv_obj.create(inv)
#             
#             self.env['account.voucher.line'].create({
# #                 'partner_id':loan.partner_id.id,
#                 'name': loan.name,
#                 'price_unit':loan.loan,
#                 'account_id':cus_acc,
#                 'type':'dr',
#                 'voucher_id':inv_id.id,
#             })
#             self.env['account.voucher.line'].create({
# #                 'partner_id':loan.partner_id.id,
#                 'name': loan.name,
#                 'price_unit':loan.interest,
#                 'account_id':int_acc,
#                 'type':'dr',
#                 'voucher_id':inv_id.id,
#             })
#                        
#             return inv_id
# 
#         for o in self:
#             res = make_voucher(o)
#             if res:
#                 print (res,res.state,res.number,'<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
# #                 if res.state in ['draft','proforma']:
#                 res.proforma_voucher()
#                 if res.move_id:
#                     for x in res.move_id.line_ids:
#                         x.write({'acc_loan_id':self.loan_id.id})
#                     self.write({'state':'return'}) 
#                         
#                     self.write({'voucher_id': res.id})
                
#         if self.voucher_id and self.voucher_id.state in ['draft', 'proforma']:
#             print (self.voucher_id.name, 'vpimtereeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')
#             self.voucher_id.proforma_voucher()
#             if self.voucher_id.move_id:
#                 for x in self.voucher_id.move_id.line_ids:
#                     x.write({'acc_loan_id':self.loan_id.id})
#                 self.write({'state':'return'}) 
#         return res

    def cheque_clear(self):
        self.write({'clear_date': time.strftime('%Y-%m-%d')})  
        self.write({'state':'done'})
        
#     def cheque_cancel(self):
#         self.write({'state':'cancel'})
    def set_draft(self):
        self.write({'state':'draft'})
        
        
    
    def post(self):
        
        date_new = datetime.datetime.today()
        list_mv_line = []
        main_amt = self.cheque_amount
        gl_code = 0.0
        gl_code_int = 0.0
        move_id = False
        move_lines_cr_capital = {}
        move_lines_cr_int = {}
        move_line_cr_int_tx = {}
        move_lines_dr = {}
        is_paid_capital = False
        is_paid_int = False
        is_paid_fee = False
        sequence_dict = {}
        total_sequnce = []
        
        name_des = "Loan Installment For: "
        move_vals = {}
        if self.loan_id.loan_type:
            for type_line in self.loan_id.loan_type.loan_component_ids:
                if type_line.type == 'principal':
                    if not type_line.gl_code:
                        raise UserError(_('Please Configure GLCode For Principal Amount'))
                    gl_code = type_line.gl_code.id
                    sequence_dict.update({type_line.sequence:type_line.type})
                    total_sequnce.append(type_line.sequence)
#                     gl_code.update({'gl_code':gl_code})
                if type_line.type == 'int_rate':
                    if not type_line.gl_code:
                        raise UserError(_('Please Configure GLCode For Interest Amount'))
                    gl_code_int = type_line.gl_code.id
                    sequence_dict.update({type_line.sequence:type_line.type})
                    total_sequnce.append(type_line.sequence)
                    
                if type_line.type == 'fees':
                    sequence_dict.update({type_line.sequence:type_line.type})
                    total_sequnce.append(type_line.sequence)
                    
#         move_vals.update({'name':'/','ref':name_des + self.loan_id.loan_id,\
#                               'date':date_new,'journal_id':self.journal_id.id,\
#                               })
#         
#         move_lines_dr.update({
#                             'account_id':self.loan_id.journal_repayment_id.default_debit_account_id.id,
#                             'name':name_des+ self.loan_id.loan_id,
#                             'debit':self.amount,
#                             'credit':0.0,
#                             'partner_id':self.loan_id.partner_id.id,
#                             
#                 })
#         list_mv_line.append((0, 0, move_lines_dr))
        
        seq_id = self.loan_id.loan_type.loan_component_ids.ids
        search_ids = self.env['loan.component.line'].search([('id','in', seq_id)],  order='sequence')
        #for type_line in search_ids: 
#         for type_line in self.loan_id.loan_type.loan_component_ids: 
        break_loop = False
        for installment_line in self.loan_id.installment_id:
            if break_loop:
                break
            for type_line in search_ids:
                move_lines_cr_capital = {}
                move_lines_cr_int = {}
                move_lines_dr = {}
                move_line_cr_int_tx = {}
                is_paid_capital = False
                is_paid_int = False
                is_paid_fee = False
                #if installment_line.state == 'draft':
                if installment_line.outstanding_prin or installment_line.outstanding_int or installment_line.outstanding_fees:
                    ## this for principal amount ....................
                    if type_line.type == 'principal':
                        if installment_line.outstanding_prin > 0.0 and  main_amt >= installment_line.outstanding_prin:
                            main_amt = main_amt - installment_line.outstanding_prin
#                             move_lines_cr_capital.update({
#                                     'account_id':gl_code,
#                                     'name':name_des+ self.loan_id.loan_id,
#                                     'credit':installment_line.outstanding_prin,
#                                     'debit':0.0,
#                                     'partner_id':self.loan_id.partner_id.id,
#                                     })
#                             list_mv_line.append((0, 0,move_lines_cr_capital))
                            installment_line.write({'outstanding_prin':0.0})
                            is_paid_capital = True
                        else:
                            if main_amt <= installment_line.outstanding_prin:
#                                 move_lines_cr_capital.update({
#                                     'account_id':gl_code,
#                                     'name':name_des+ self.loan_id.loan_id,
#                                     'credit':main_amt,
#                                     'debit':0.0,
#                                     'partner_id':self.loan_id.partner_id.id,
#                                     })
                                main_amt = installment_line.outstanding_prin - main_amt
                                installment_line.write({'outstanding_prin':main_amt})
#                                 list_mv_line.append((0, 0, move_lines_cr_capital))
                                break_loop = True
                                break
                            if is_paid_capital and is_paid_fee and is_paid_int:
                                installment_line.write({'state':'paid'})
#                             else:
#                                 installment_line.write({'state':'open'})
                    
                    ## next for interest amount ..............
                    if type_line.type == 'int_rate':
                        if installment_line.outstanding_int > 0.0 and main_amt >= installment_line.outstanding_int:
                            if type_line.tax_id:
                                tx_tot_int = self.get_tax_total(type_line.tax_id, installment_line.outstanding_int)
                                new_amt = installment_line.outstanding_int - tx_tot_int
#                                 move_lines_cr_int.update({
#                                         'account_id':gl_code_int,
#                                         'name':name_des+ self.loan_id.loan_id,
#                                         'credit':new_amt,
#                                         'debit':0.0,
#                                         'partner_id':self.loan_id.partner_id.id,
#                                         })
                                
#                                 list_mv_line.append((0, 0, move_lines_cr_int))
#                                 if tx_tot_int:
#                                     move_line_cr_int_tx.update({
#                                                                     'account_id':type_line.tax_id.account_id.id,
#                                                                     'name':name_des+ self.loan_id.loan_id,
#                                                                     'credit':tx_tot_int,
#                                                                     'debit':0.0,
#                                                                     'partner_id':self.loan_id.partner_id.id,
#                                         })
#                                     list_mv_line.append((0, 0, move_line_cr_int_tx))
                                
#                             else:
#                                 move_lines_cr_int.update({
#                                         'account_id':gl_code_int,
#                                         'name':name_des+ self.loan_id.loan_id,
#                                         'credit':installment_line.outstanding_int,
#                                         'debit':0.0,
#                                         'partner_id':self.loan_id.partner_id.id,
#                                         })
#                                 list_mv_line.append((0, 0, move_lines_cr_int))
                                
                            main_amt = main_amt - installment_line.outstanding_int
                            installment_line.write({'outstanding_int':0.0})
                            is_paid_int = True
                            
                        else:
                            if main_amt <= installment_line.outstanding_int:
                                if type_line.tax_id:
                                    tx_tot_int = self.get_tax_total(type_line.tax_id, main_amt)
                                    new_amt = main_amt - tx_tot_int
#                                     move_lines_cr_int.update({
#                                             'account_id':gl_code_int,
#                                             'name':name_des+ self.loan_id.loan_id,
#                                             'credit':new_amt,
#                                             'debit':0.0,
#                                             'partner_id':self.loan_id.partner_id.id,
#                                             })
#                                     
#                                     list_mv_line.append((0, 0, move_lines_cr_int))
#                                     if tx_tot_int:
#                                         move_line_cr_int_tx.update({
#                                                                     'account_id':type_line.tax_id.account_id.id,
#                                                                     'name':name_des+ self.loan_id.loan_id,
#                                                                     'credit':tx_tot_int,
#                                                                     'debit':0.0,
#                                                                     'partner_id':self.loan_id.partner_id.id,
#                                                                     })
#                                         
#                                         list_mv_line.append((0, 0, move_line_cr_int_tx))
#                                 else:
#                                     move_lines_cr_int.update({
#                                             'account_id':gl_code_int,
#                                             'name':name_des+ self.loan_id.loan_id,
#                                             'credit':main_amt,
#                                             'debit':0.0,
#                                             'partner_id':self.loan_id.partner_id.id,
#                                             })
                                main_amt = installment_line.outstanding_int - main_amt
                                installment_line.write({'outstanding_int':main_amt})
    #                                 if is_paid_int:
#                                     installment_line.write({'state':'paid'})
                                break_loop = True
                                break
                            if is_paid_capital and is_paid_fee and is_paid_int:
                                installment_line.write({'state':'paid'})
                    ##next for fees calculation ............
                    if type_line.type == 'fees':
                        if not type_line.gl_code:
                            raise UserError(_('Please Configure GLCode For fees Amount'))
                        for fees_line in installment_line.fee_lines:
                            fees_dict = {}
                            interest_dict = {}
                            if fees_line.product_id.id == type_line.product_id.id and fees_line.is_paid == False:
                                fees_line_base = fees_line.base - fees_line.base_paid
                                fees_line_tax = fees_line.tax - fees_line.tax_paid
                                
                                if fees_line_base > 0.0 and main_amt >= fees_line_base + fees_line_tax:
                                    total_paid_amount = 0
                                    if fees_line_base:
                                        base_amt = fees_line_base
                                        fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':base_amt})
                                        total_paid_amount = total_paid_amount + base_amt
                                    if type_line.tax_id:
                                        tx_tot = fees_line_tax
                                        interest_dict = self.get_interest_vals(tx_tot, type_line.tax_id.account_id)
                                        total_paid_amount = total_paid_amount + tx_tot
                                        
                                    fees_line.write({'base_paid':base_amt + fees_line.base_paid, 'tax_paid':fees_line_tax + fees_line.tax_paid, 'is_paid':True})
#                                     if fees_dict:
#                                             list_mv_line.append((0, 0, fees_dict))
#                                     if interest_dict:
#                                         list_mv_line.append((0, 0, interest_dict))
                                    if fees_line_tax:
                                        main_amt = main_amt - (fees_line_base + fees_line_tax)
                                    else:
                                        main_amt = main_amt - fees_line_base 
                                        
                                    installment_line.outstanding_fees = installment_line.outstanding_fees - total_paid_amount
                                    
                                else:
                                    if main_amt >= fees_line_base:
                                        total_paid_amount = 0
                                        base_amt = fees_line_base
                                        base_paid = False
                                        tax_paid = False
                                        if fees_line_base:
                                            fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':fees_line_base})
                                            total_paid_amount = total_paid_amount + fees_line_base
#                                             list_mv_line.append((0, 0, fees_dict))
                                            base_paid = True
                                            fees_line.write({'base_paid':fees_line_base  + fees_line.base_paid})
                                        if fees_line_base == 0.0:
                                            base_paid = True
                                        rem = main_amt - fees_line_base
                                        
                                        main_amt = rem
                                        
                                        if fees_line_tax and rem >= fees_line_tax:
#                                             interest_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':fees_line_tax})
                                            interest_dict = self.get_interest_vals(fees_line_tax, type_line.tax_id.account_id)
                                            total_paid_amount = total_paid_amount + fees_line_tax
#                                             if fees_line_tax:
#                                                 list_mv_line.append((0, 0, interest_dict))
                                            tax_paid = True
                                            fees_line.write({'tax_paid':fees_line_tax + fees_line.tax_paid})
                                            if total_paid_amount: installment_line.outstanding_fees = installment_line.outstanding_fees - total_paid_amount
                                            main_amt = rem - fees_line_tax
                                            if not main_amt:
                                                break_loop = True
                                                break
                                            
                                        else:
#                                             interest_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':rem})
                                            if fees_line_tax:
                                                interest_dict = self.get_interest_vals(rem, type_line.tax_id.account_id)
                                                total_paid_amount = total_paid_amount + rem
#                                                 list_mv_line.append((0, 0, interest_dict))
                                                fees_line.write({'tax_paid':rem + fees_line.tax_paid})
                                                if total_paid_amount: installment_line.outstanding_fees = installment_line.outstanding_fees - total_paid_amount
                                                main_amt = 0.0
                                                break_loop = True
                                                break
                                        
                                        if base_paid and tax_paid: fees_line.is_paid = True
                                    else:
                                        fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':main_amt})
                                        installment_line.outstanding_fees = installment_line.outstanding_fees - main_amt
#                                         list_mv_line.append((0, 0, fees_dict))
                                        fees_line.write({'base_paid':main_amt + fees_line.base_paid})
                                        main_amt = 0.0
                                        
                                        break 
                        if not main_amt:
                            break_loop = True
                            break
            if not installment_line.outstanding_prin and not installment_line.outstanding_int and not installment_line.outstanding_fees:
                installment_line.state = 'paid' 
#             else:
#                 installment_line.write({'state':'open'}) 
        if main_amt:
            print ("code do for extra paymenf") 
        return True
                               
