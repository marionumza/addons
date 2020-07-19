from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from dateutil.relativedelta import relativedelta
from datetime import date
import datetime
from pickle import INST


class LoanPaymentDetails(models.Model):
    _name = 'payment.details'
    _description = "Payment Details"
    
    name = fields.Char("Payment type")
    pay_date = fields.Date("Date")
    move_id = fields.Many2one('account.move')
    line_id = fields.Many2one('account.loan.installment')
    prin_amt = fields.Float("Principal Amount")
    int_amt = fields.Float("Interest Amount")
    fees_amt = fields.Float("Fees Amount")
    base_fee_paid = fields.Float("Base Fee Paid")
    base_fee_tax_paid = fields.Float("Base Fee Tax Paid")
    late_fee_amt = fields.Float("Late Fee Amount")
    base_late_fee_amt = fields.Float("Base Paid Late Fee")
    base_late_fee_amt_tx = fields.Float("Late Fee Amount Tax")
    state = fields.Selection([('draft','Draft'),('cancel','Cancel')], string="State")
    


class LoanPayment(models.Model):
    
    _name = 'loan.payment'
    _description = "Loan Payment"
    
    name = fields.Char(readonly=True, copy=False) # The name is attributed upon post()
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    amount = fields.Monetary(string='Payment Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    loan_id = fields.Many2one('account.loan', "Loan Ref.")
    late_fee = fields.Float(string='Late Fees')
    is_late_fee = fields.Boolean("Is Late Fee")
    
    @api.model
    def default_get(self, fields):
        rec = super(LoanPayment, self).default_get(fields)
        if not self._context:
            return rec
        active_id = self._context.get('active_id')
        loan_id = self.env[self._context.get('active_model')].browse(active_id)
        if loan_id.journal_repayment_id:
            rec['journal_id'] = loan_id.journal_repayment_id.id
            rec['loan_id'] = loan_id.id
         
        current_date = datetime.date.today()
        total = 0.0
        for line in loan_id.installment_id:
            if line.state != 'paid' and line.date:
                # date_object = (datetime.datetime.strptime(line.date, '%Y-%m-%d').date()+relativedelta(days = loan_id.grace_period))
                date_object = (line.date+relativedelta(days = loan_id.grace_period))
                if current_date >= date_object:
                    rec['is_late_fee'] = True
                total += line.late_fee
        rec['late_fee'] = total
        return rec
    
    @api.onchange('journal_id')
    def _onchange_disburse_journal(self):
        if self.journal_id:
            active_id = self._context.get('active_id')
            acc_loan = self.env['account.loan'].browse(active_id)
            self.currency_id = self.journal_id.currency_id or acc_loan.company_id.currency_id
            
    
    @api.multi
    def action_validate_loan_payment(self):
        """ Posts a payment of loan installment.
        """
        print ('to do tsk remain to do..................................')
        if self.amount == 0.0:
            raise UserError(_("Please Enter Installment Amount."))
        if any(len(record.loan_id) != 1 for record in self):
            raise UserError(_("This method should only be called to process a single loan's payment."))
        move_id = self.post()
        for line in move_id.line_ids:
            self.loan_id.write({'move_id':[(4,line.id)]})
            
        repayment_obj = self.env['account.loan.repayment']
#         search_id = repayment_obj.search([('is_button_visible','=',True)])
#         if search_id: search_id.is_button_visible = False     
        payment_id = self.env['account.loan.repayment'].create({
             'name' : self.loan_id.partner_id.id,
             'pay_date' : self.payment_date,
            'amt' : self.amount,
            'loan_id' : self.loan_id.id,
            'release_number': move_id.id,
            'is_button_visible':True
            })
        self.loan_id.write({'repayment_details':[(4,payment_id.id)]})
        return move_id
    
    
    
    ##calculate taxes for non included .......................
    def get_interest_vals(self, tx_tot, account_id):
        if tx_tot:
            taxes_lines = {}
            taxes_lines.update({'partner_id':self.loan_id.partner_id.id,'account_id':account_id.id, 'debit':0.0, 'credit':tx_tot})
            return taxes_lines
    
    def get_fees_vals(self, type_line):
        
        fees = {}
        if type_line.product_amt:
            fees.update({'partner_id':self.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':type_line.product_amt})
        return fees
    
    ## total calculatin of tax for fee calculation in installment ................
    def get_tax_total(self, tx_ids, amount):
        tax_amt = 0.0
        for tx in tx_ids:
            tax = round(amount - ((amount * 100) / (100 + tx.amount)),2)
            tax_amt = tax_amt + tax
        return tax_amt
    
    ## get value without taxess .............
    def get_tax_value(self, tax_ids, amount):
        amt = 0.0
        for tx in tax_ids:
            tax = 100
            tax = tax + tx.amount
            amt = (amount * 100) / tax
        return amt
    @api.multi
    def post(self):
        
        date_new = self.payment_date
        list_mv_line = []
        if self.late_fee > 0.0:
            late_fee = self.late_fee
            main_amt = self.amount - self.late_fee
        else:
            late_fee = self.late_fee
            main_amt = self.amount
            
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
        amount = 0.0
        amount_currency = False
        today = datetime.datetime.today().date()
        
        if not self.loan_id.company_id.currency_id:
            raise UserError('Please Define Company Currency')
        company_curren = self.loan_id.company_id.currency_id
        
        if not self.currency_id:
                raise UserError('Please Define Company Currency')
        currency_id = self.currency_id
        
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
                    
        move_vals.update({'name':'/','ref':name_des + self.loan_id.loan_id,\
                              'date':date_new,'journal_id':self.journal_id.id,\
                              })
        if currency_id.id != company_curren.id:
            amount_currency = self.amount
            amount = company_curren.with_context(date=date_new).compute(self.amount, currency_id)
        else:
            amount_currency = False
        if not amount_currency:
            move_lines_dr.update({
                                'account_id':self.journal_id.default_debit_account_id.id,
                                'name':name_des+ self.loan_id.loan_id,
                                'debit':self.amount,
                                'credit':0.0,
                                'partner_id':self.loan_id.partner_id.id,
                                
                    })
        else:
            move_lines_dr.update({
                                'account_id':self.journal_id.default_debit_account_id.id,
                                'name':name_des+ self.loan_id.loan_id,
                                'debit':amount,
                                'credit':0.0,
                                'partner_id':self.loan_id.partner_id.id,
                                'amount_currency':amount_currency,
                                'currency_id':currency_id.id
                                
                    })
            
        list_mv_line.append((0, 0, move_lines_dr))
        
        seq_id = self.loan_id.loan_type.loan_component_ids.ids
        search_ids = self.env['loan.component.line'].search([('id','in', seq_id)],  order='sequence')
        #for type_line in search_ids: 
#         for type_line in self.loan_id.loan_type.loan_component_ids: 
        break_loop = False
        affected_line_list = []
        for installment_line in self.loan_id.installment_id:
#             if self.loan_id.journal_disburse_id:
#                 if self.loan_id.journal_disburse_id.currency_id:
#                     journal_currency = self.loan_id.journal_disburse_id.currency_id
#                 else:
#                     journal_currency = self.loan_id.journal_disburse_id.company_id.currency_id
                        
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
                    if installment_line not in affected_line_list:
                        affected_line_list.append(installment_line)
                    if type_line.type == 'principal':
                        if installment_line.outstanding_prin > 0.0 and  main_amt >= installment_line.outstanding_prin:
                            main_amt = main_amt - installment_line.outstanding_prin
                            if currency_id.id != company_curren.id:
                                amount_currency = installment_line.outstanding_prin
                                amount = company_curren.with_context(date=date_new).compute(installment_line.outstanding_prin, currency_id)
                            else:
                                amount_currency = False
                            if not amount_currency:
                                move_lines_cr_capital.update({
                                        'account_id':gl_code,
                                        'name':name_des+ self.loan_id.loan_id,
                                        'credit':installment_line.outstanding_prin,
                                        'debit':0.0,
                                        'partner_id':self.loan_id.partner_id.id,
                                        })
                                installment_line.with_context({'prin':installment_line.outstanding_prin}).onchange_principle()
                            else:
                                move_lines_cr_capital.update({
                                        'account_id':gl_code,
                                        'name':name_des+ self.loan_id.loan_id,
                                        'credit':amount,
                                        'debit':0.0,
                                        'partner_id':self.loan_id.partner_id.id,
                                        'amount_currency':-amount_currency,
                                        'currency_id':currency_id.id
                                        })
                                installment_line.with_context({'prin':amount}).onchange_principle()
                            list_mv_line.append((0, 0,move_lines_cr_capital))
                            installment_line.write({'outstanding_prin':0.0,'due_principal':0.0,'paid_prin':installment_line.outstanding_prin})
                            is_paid_capital = True
                            
                            if not main_amt:
                                if not late_fee:
                                    break_loop = True 
                                break
                        else:
                            if main_amt <= installment_line.outstanding_prin:
                                main_amt = round(main_amt,2)
                                if currency_id.id != company_curren.id:
                                    amount_currency = main_amt
                                    amount = company_curren.with_context(date=date_new).compute(main_amt, currency_id)
                                else:
                                    amount_currency = False
                                if not amount_currency:
                                    move_lines_cr_capital.update({
                                        'account_id':gl_code,
                                        'name':name_des+ self.loan_id.loan_id,
                                        'credit':main_amt,
                                        'debit':0.0,
                                        'partner_id':self.loan_id.partner_id.id,
                                        })
                                    installment_line.with_context({'prin':main_amt}).onchange_principle()
                                else:
                                    move_lines_cr_capital.update({
                                        'account_id':gl_code,
                                        'name':name_des+ self.loan_id.loan_id,
                                        'credit':amount,
                                        'debit':0.0,
                                        'partner_id':self.loan_id.partner_id.id,
                                        'amount_currency':-amount_currency,
                                        'currency_id':currency_id.id
                                        })
                                    installment_line.with_context({'prin':amount}).onchange_principle()
                                main_amt = installment_line.outstanding_prin - main_amt
                                # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                if installment_line.date <= today:
                                    installment_line.write({'outstanding_prin':main_amt,'due_principal':main_amt, 'paid_prin': installment_line.outstanding_prin -main_amt})
                                else:
                                    installment_line.write({'outstanding_prin':main_amt,'due_principal':0.0, 'paid_prin':installment_line.outstanding_prin - main_amt})
                                list_mv_line.append((0, 0, move_lines_cr_capital))
                                main_amt = 0.0
                                if not late_fee:
                                    break_loop = True
                                break
                            if is_paid_capital and is_paid_fee and is_paid_int:
                                installment_line.write({'state':'paid'})
                    
                    ## next for interest amount ..............
                    if type_line.type == 'int_rate':
                        if installment_line.outstanding_int > 0.0 and main_amt >= installment_line.outstanding_int:
                            if type_line.tax_id:
                                tx_tot_int = self.get_tax_total(type_line.tax_id, installment_line.outstanding_int)
                                new_amt = round(installment_line.outstanding_int - tx_tot_int, 2)
                                if currency_id.id != company_curren.id:
                                    amount_currency = new_amt
                                    amount = company_curren.with_context(date=date_new).compute(new_amt, currency_id)
                                else:
                                    amount_currency = False
                                if not amount_currency:
                                    move_lines_cr_int.update({
                                            'account_id':gl_code_int,
                                            'name':name_des+ self.loan_id.loan_id,
                                            'credit':new_amt,
                                            'debit':0.0,
                                            'partner_id':self.loan_id.partner_id.id,
                                            })
                                    installment_line.with_context({'int':new_amt}).onchange_interest()
                                else:
                                    move_lines_cr_int.update({
                                            'account_id':gl_code_int,
                                            'name':name_des+ self.loan_id.loan_id,
                                            'credit':amount,
                                            'debit':0.0,
                                            'partner_id':self.loan_id.partner_id.id,
                                            'amount_currency':-amount_currency,
                                            'currency_id':currency_id.id
                                            })
                                    installment_line.with_context({'int':amount}).onchange_interest()
                                
                                list_mv_line.append((0, 0, move_lines_cr_int))
                                if tx_tot_int:
                                    if currency_id.id != company_curren.id:
                                        amount_currency = tx_tot_int
                                        amount = company_curren.with_context(date=date_new).compute(tx_tot_int, currency_id)
                                    else:
                                        amount_currency = False
                                    if not amount_currency:
                                        move_line_cr_int_tx.update({
                                                'account_id':type_line.tax_id.account_id.id,
                                                'name':name_des+ self.loan_id.loan_id,
                                                'credit':tx_tot_int,
                                                'debit':0.0,
                                                'partner_id':self.loan_id.partner_id.id,
                                            })
                                        installment_line.with_context({'int':tx_tot_int}).onchange_interest()
                                    else:
                                        move_line_cr_int_tx.update({
                                                'account_id':type_line.tax_id.account_id.id,
                                                'name':name_des+ self.loan_id.loan_id,
                                                'credit':amount,
                                                'debit':0.0,
                                                'partner_id':self.loan_id.partner_id.id,
                                                'amount_currency':-amount_currency,
                                                'currency_id':currency_id.id
                                            })
                                        installment_line.with_context({'int':amount}).onchange_interest()
                                        
                                    list_mv_line.append((0, 0, move_line_cr_int_tx))
                                
                            else:
                                if currency_id.id != company_curren.id:
                                        amount_currency = installment_line.outstanding_int
                                        amount = company_curren.with_context(date=date_new).compute(installment_line.outstanding_int, currency_id)
                                else:
                                    amount_currency = False
                                if not amount_currency:
                                    move_lines_cr_int.update({
                                            'account_id':gl_code_int,
                                            'name':name_des+ self.loan_id.loan_id,
                                            'credit':installment_line.outstanding_int,
                                            'debit':0.0,
                                            'partner_id':self.loan_id.partner_id.id,
                                            })
                                    installment_line.with_context({'int':installment_line.outstanding_int}).onchange_interest()
                                else:
                                    move_lines_cr_int.update({
                                            'account_id':gl_code_int,
                                            'name':name_des+ self.loan_id.loan_id,
                                            'credit':amount,
                                            'debit':0.0,
                                            'partner_id':self.loan_id.partner_id.id,
                                            'amount_currency':-amount_currency,
                                            'currency_id':currency_id.id
                                            })
                                    installment_line.with_context({'int':amount}).onchange_interest()
                                    
                                list_mv_line.append((0, 0, move_lines_cr_int))
                            
                            main_amt = main_amt - installment_line.outstanding_int
                            installment_line.write({'outstanding_int':0.0,'due_interest':0.0,'paid_int':installment_line.outstanding_int})
                            is_paid_int = True
                            
                            if not main_amt:
                                if not late_fee:
                                    break_loop = True
                                break
                            
                        else:
                            if main_amt <= installment_line.outstanding_int:
                                main_amt = round(main_amt, 2)
                                if type_line.tax_id:
                                    tx_tot_int = self.get_tax_total(type_line.tax_id, main_amt)
                                    new_amt = main_amt - tx_tot_int
                                    
                                    if currency_id.id != company_curren.id:
                                        amount_currency = new_amt
                                        amount = company_curren.with_context(date=date_new).compute(new_amt, currency_id)
                                    else:
                                        amount_currency = False
                                    if not amount_currency:
                                        move_lines_cr_int.update({
                                                'account_id':gl_code_int,
                                                'name':name_des+ self.loan_id.loan_id,
                                                'credit':new_amt,
                                                'debit':0.0,
                                                'partner_id':self.loan_id.partner_id.id,
                                                })
                                        installment_line.with_context({'int':new_amt}).onchange_interest()
                                    else:
                                        move_lines_cr_int.update({
                                                'account_id':gl_code_int,
                                                'name':name_des+ self.loan_id.loan_id,
                                                'credit':amount,
                                                'debit':0.0,
                                                'partner_id':self.loan_id.partner_id.id,
                                                'amount_currency':-amount_currency,
                                                'currency_id':currency_id.id
                                                })
                                        installment_line.with_context({'int':amount}).onchange_interest()
                                    
                                    list_mv_line.append((0, 0, move_lines_cr_int))
                                    if tx_tot_int:
                                        if currency_id.id != company_curren.id:
                                            amount_currency = tx_tot_int
                                            amount = company_curren.with_context(date=date_new).compute(tx_tot_int, currency_id)
                                        else:
                                            amount_currency = False
                                        if not amount_currency:
                                            move_line_cr_int_tx.update({
                                                    'account_id':type_line.tax_id.account_id.id,
                                                    'name':name_des+ self.loan_id.loan_id,
                                                    'credit':tx_tot_int,
                                                    'debit':0.0,
                                                    'partner_id':self.loan_id.partner_id.id,
                                                    })
                                            installment_line.with_context({'int':tx_tot_int}).onchange_interest()
                                        else:
                                            move_line_cr_int_tx.update({
                                                    'account_id':type_line.tax_id.account_id.id,
                                                    'name':name_des+ self.loan_id.loan_id,
                                                    'credit':amount,
                                                    'debit':0.0,
                                                    'partner_id':self.loan_id.partner_id.id,
                                                    'amount_currency':-amount_currency,
                                                    'currency_id':currency_id.id
                                                    })
                                            installment_line.with_context({'int':amount}).onchange_interest()
                                        list_mv_line.append((0, 0, move_line_cr_int_tx))
                                else:
                                    if currency_id.id != company_curren.id:
                                            amount_currency = main_amt
                                            amount = company_curren.with_context(date=date_new).compute(main_amt, currency_id)
                                    else:
                                        amount_currency = False
                                    if not amount_currency:
                                        move_lines_cr_int.update({
                                                'account_id':gl_code_int,
                                                'name':name_des+ self.loan_id.loan_id,
                                                'credit':main_amt,
                                                'debit':0.0,
                                                'partner_id':self.loan_id.partner_id.id,
                                                })
                                        installment_line.with_context({'int':main_amt}).onchange_interest()
                                    else:
                                        move_lines_cr_int.update({
                                                'account_id':gl_code_int,
                                                'name':name_des+ self.loan_id.loan_id,
                                                'credit':amount,
                                                'debit':0.0,
                                                'partner_id':self.loan_id.partner_id.id,
                                                'amount_currency':-amount_currency,
                                                'currency_id':currency_id.id
                                                })
                                        installment_line.with_context({'int':amount}).onchange_interest()
                                    list_mv_line.append((0, 0, move_lines_cr_int))
                                    
                                main_amt = installment_line.outstanding_int - main_amt
                                # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                if installment_line.date <= today:
                                    installment_line.write({'outstanding_int':main_amt,'due_interest':main_amt, 'paid_int':installment_line.outstanding_int - main_amt})
                                else:
                                    installment_line.write({'outstanding_int':main_amt,'due_interest': 0.0, 'paid_int':installment_line.outstanding_int - main_amt})
                                main_amt = 0.0
#                                 list_mv_line.append((0, 0, move_lines_cr_int))
    #                                 if is_paid_int:
#                                     installment_line.write({'state':'paid'})
                                if not late_fee:
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
                                fees_line_base = round(fees_line.base - fees_line.base_paid, 2)
                                fees_line_tax = round(fees_line.tax - fees_line.tax_paid, 2)
                                ##tax calculation for payment wise spliting ..............
#                                 if fees_line.tax_paid:
#                                     tx_cal_amt = self.get_tax_total(type_line.tax_id, main_amt)
                                print (fees_line_base,'base paiddddddddddddddddddddddd')
                                if fees_line_base > 0.0 and main_amt >= fees_line_base + fees_line_tax:
                                    total_paid_amount = 0
                                    if type_line.tax_id:
                                        rm_tx = self.get_tax_value(type_line.tax_id, fees_line_base)
                                        fees_line_tax = fees_line_base - rm_tx
                                        fees_line_base = fees_line_base - fees_line_tax
                                    if fees_line_base:
                                        base_amt = fees_line_base
                                        if currency_id.id != company_curren.id:
                                            amount_currency = base_amt
                                            amount = company_curren.with_context(date=date_new).compute(base_amt, currency_id)
                                        else:
                                            amount_currency = False
                                        if not amount_currency:
                                            fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':base_amt})
                                        else:
                                            fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,\
                                                              'debit':0.0, 'credit':amount, 'amount_currency':-amount_currency,
                                                              'currency_id':currency_id.id })
                                        installment_line.with_context({'fee':fees_dict.get('credit')}).onchange_fees()
                                            
                                        total_paid_amount = total_paid_amount + base_amt
                                    if type_line.tax_id:
                                        tx_tot = fees_line_tax
                                        if currency_id.id != company_curren.id:
                                            amount_currency = tx_tot
                                            amount = company_curren.with_context(date=date_new).compute(tx_tot, currency_id)
                                        else:
                                            amount_currency = False
                                        if not amount_currency:
                                            interest_dict = self.get_interest_vals(tx_tot, type_line.tax_id.account_id)
                                        else:
                                            interest_dict.update({'partner_id':self.loan_id.partner_id.id,\
                                                                  'account_id':type_line.tax_id.account_id.id,\
                                                                  'debit':0.0, 'credit':amount, 'amount_currency':-amount_currency,'currency_id':currency_id.id})
                                        if interest_dict:
                                            installment_line.with_context({'fee':interest_dict.get('credit')}).onchange_fees()
                                        total_paid_amount = total_paid_amount + tx_tot
                                        installment_line.paid_fees_tx = tx_tot
                                        
#                                     fees_line.write({'base_paid':base_amt + fees_line.base_paid, 'tax_paid':fees_line_tax + fees_line.tax_paid, 'is_paid':True})
                                    fees_line.write({'base_paid':base_amt + fees_line.base_paid + fees_line_tax, 'is_paid':True})
                                    if fees_dict:
                                            list_mv_line.append((0, 0, fees_dict))
                                    if interest_dict:
                                        list_mv_line.append((0, 0, interest_dict))
                                    if fees_line_tax:
                                        main_amt = round(main_amt - (fees_line_base + fees_line_tax), 2)
                                    else:
                                        main_amt = round(main_amt - fees_line_base, 2)
                                    
                                    installment_line.paid_fees = base_amt
                                    installment_line.outstanding_fees = installment_line.outstanding_fees - total_paid_amount
                                    # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                    if installment_line.date <= today:
                                        installment_line.due_fees = installment_line.outstanding_fees
                                    if not main_amt:
                                        if not late_fee:
                                            break_loop = True
                                        break
                                else:
                                    if main_amt >= fees_line_base:
                                        total_paid_amount = 0
                                        if fees_line.tax:
                                            tx_cal_amt = self.get_tax_total(type_line.tax_id, main_amt)
                                            fees_line_base = main_amt - tx_cal_amt
                                            
                                        base_amt = fees_line_base
                                        base_paid = False
                                        tax_paid = False
                                        if fees_line_base:
                                            if currency_id.id != company_curren.id:
                                                amount_currency = fees_line_base
                                                amount = company_curren.with_context(date=date_new).compute(fees_line_base, currency_id)
                                            else:
                                                amount_currency = False
                                            if not amount_currency:
                                                fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':fees_line_base})
                                            else:
                                                fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,\
                                                                  'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                                  'currency_id':currency_id.id})
                                            installment_line.with_context({'fee':fees_dict.get('credit')}).onchange_fees()
#                                             total_paid_amount = total_paid_amount + fees_line_base
                                            list_mv_line.append((0, 0, fees_dict))
                                            base_paid = True
                                            installment_line.outstanding_fees = installment_line.outstanding_fees - fees_line_base
                                            installment_line.paid_fees = fees_line_base
                                            # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                            if installment_line.date <= today:
                                                installment_line.due_fees = installment_line.outstanding_fees
                                            else:
                                                installment_line.due_fees = 0.0
                                            fees_line.write({'base_paid':fees_line_base  + fees_line.base_paid})
                                            main_amt = round(main_amt,2)
                                            rem = main_amt - fees_line_base
                                            main_amt = rem
                                            
                                            
                                        if main_amt >=fees_line_tax:
                                            ## new changes done hereesssssss for payment calculation ......
                                            tx_amt = 0.0
                                            if type_line.tax_id:
                                                tx_cal_amt = self.get_tax_total(type_line.tax_id, fees_line_tax)
                                                tx_amt = main_amt - tx_cal_amt
#                                                 tx_amt = fees_line_tax
                                                if tx_amt:
                                                    fees_dict_tx = {}
                                                    fees_line_tax = fees_line_tax - tx_amt
                                                    if currency_id.id != company_curren.id:
                                                        amount_currency = tx_amt
                                                        amount = company_curren.with_context(date=date_new).compute(tx_amt, currency_id)
                                                    else:
                                                        amount_currency = False
                                                    if type_line.tax_id:
                                                        gl_acc = type_line.tax_id.account_id.id
                                                    else:
                                                        gl_acc = type_line.gl_code.id
                                                    if not amount_currency:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,'debit':0.0, 'credit':tx_amt})
                                                    else:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,\
                                                                          'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                                          'currency_id':currency_id.id})
                                                    installment_line.with_context({'fee':fees_dict_tx.get('credit')}).onchange_fees()
#                                                     total_paid_amount = total_paid_amount + tx_amt
                                                    list_mv_line.append((0, 0, fees_dict_tx))
                                                    installment_line.outstanding_fees = installment_line.outstanding_fees - tx_amt
                                                    fees_line.write({'tax_paid':tx_amt  + fees_line.tax_paid})
                                                    installment_line.paid_fees_tx = tx_amt
                                                    # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                                    if installment_line.date <= today:
                                                        installment_line.due_fees = installment_line.outstanding_fees
                                                    else:
                                                        installment_line.due_fees = 0.0
                                                    tax_paid = True
                                                    main_amt = round(main_amt,2)
                                                    rem = main_amt - tx_amt
                                                    main_amt = rem
                                        else:
                                            tx_amt = 0.0
                                            if type_line.tax_id:
                                                tx_amt = main_amt
                                                if tx_amt:
                                                    fees_dict_tx = {}
                                                    fees_line_tax = fees_line_tax - tx_amt
                                                    if currency_id.id != company_curren.id:
                                                        amount_currency = tx_amt
                                                        amount = company_curren.with_context(date=date_new).compute(tx_amt, currency_id)
                                                    else:
                                                        amount_currency = False
                                                    if type_line.tax_id:
                                                        gl_acc = type_line.tax_id.account_id.id
                                                    else:
                                                        gl_acc = type_line.gl_code.id
                                                    if not amount_currency:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,'debit':0.0, 'credit':tx_amt})
                                                    else:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,\
                                                                          'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                                          'currency_id':currency_id.id})
                                                    installment_line.with_context({'fee':fees_dict_tx.get('credit')}).onchange_fees()
#                                                     total_paid_amount = total_paid_amount + tx_amt
                                                    list_mv_line.append((0, 0, fees_dict_tx))
                                                    fees_line.write({'tax_paid':tx_amt  + fees_line.tax_paid})
                                                    installment_line.outstanding_fees = installment_line.outstanding_fees - tx_amt
                                                    installment_line.paid_fees_tx = tx_amt
                                                    # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                                    if installment_line.date <= today:
                                                        installment_line.due_fees = installment_line.outstanding_fees
                                                    else:
                                                        installment_line.due_fees = 0.0
#                                                     fees_line.write({'tax_paid':rem + fees_line.tax_paid})
                                                    if not fees_line_tax:
                                                        tax_paid = True
                                                    main_amt = 0.0
                                                    
                                        if not fees_line_base:
                                            base_paid = True
                                        if base_paid and tax_paid: fees_line.is_paid = True
                                        if not main_amt:
                                            if not late_fee:
                                                break_loop = True
                                            break
                                    else:
                                        rem_fr_tx_amt = 0.0
                                        tx_cal_amt = 0.0
                                        if main_amt > 0.0:
                                            if type_line.tax_id:
#                                                 tx_cal_amt = self.get_tax_total(type_line.tax_id, main_amt)
                                                tx_amt = self.get_tax_value(type_line.tax_id, main_amt)
                                                tx_cal_amt = main_amt - tx_amt
                                                main_amt = main_amt - tx_cal_amt
                                            else:
                                                main_amt = round(main_amt, 2)
                                            if currency_id.id != company_curren.id:
                                                amount_currency = main_amt
                                                amount = company_curren.with_context(date=date_new).compute(main_amt, currency_id)
                                            else:
                                                amount_currency = False
#                                             if type_line.tax_id:
#                                                 gl_acc = type_line.tax_id.account_id.id
#                                             else:
                                            gl_acc = type_line.gl_code.id
                                            if not amount_currency:
                                                fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,'debit':0.0, 'credit':main_amt})
                                            else:
                                                fees_dict.update({'partner_id':self.loan_id.partner_id.id,\
                                                                  'account_id':gl_acc,'debit':0.0,\
                                                                   'credit':amount,'amount_currency':-amount_currency,\
                                                                   'currency_id':currency_id.id})
                                            installment_line.with_context({'fee':fees_dict.get('credit')}).onchange_fees()
                                            
                                            installment_line.outstanding_fees = installment_line.outstanding_fees - main_amt
                                            installment_line.paid_fees = main_amt
                                            # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                            if installment_line.date <= today:
                                                installment_line.due_fees = installment_line.outstanding_fees
                                            else:
                                                installment_line.due_fees = 0.0
                                            list_mv_line.append((0, 0, fees_dict))
                                            fees_line.write({'base_paid':main_amt + fees_line.base_paid})
                                            
                                            if tx_cal_amt:
                                                rem_fr_tx_amt = tx_cal_amt
                                            if not rem_fr_tx_amt:
                                                main_amt = 0.0
                                                break 
                                            
                                        ##recent changes ...........................
                                        if rem_fr_tx_amt:
                                            tx_amt = rem_fr_tx_amt
                                            if tx_amt:
                                                fees_dict_tx = {}
#                                                 fees_line_tax = tx_amt
                                                if currency_id.id != company_curren.id:
                                                    amount_currency = tx_amt
                                                    amount = company_curren.with_context(date=date_new).compute(tx_amt, currency_id)
                                                else:
                                                    amount_currency = False
                                                if type_line.tax_id:
                                                    gl_acc = type_line.tax_id.account_id.id
                                                else:
                                                    gl_acc = type_line.gl_code.id
                                                if not amount_currency:
                                                    fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,'debit':0.0, 'credit':tx_amt})
                                                else:
                                                    fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,\
                                                                      'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                                      'currency_id':currency_id.id})
                                                installment_line.with_context({'fee':fees_dict_tx.get('credit')}).onchange_fees()
#                                                     total_paid_amount = total_paid_amount + tx_amt
                                                list_mv_line.append((0, 0, fees_dict_tx))
                                                installment_line.outstanding_fees = installment_line.outstanding_fees - tx_amt
#                                                 fees_line.write({'tax_paid':tx_amt  + fees_line.tax_paid})
                                                fees_line.write({'base_paid':tx_amt  + fees_line.tax_paid + fees_line.base_paid})
                                                installment_line.paid_fees_tx = tx_amt
                                                # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                                if installment_line.date <= today:
                                                    installment_line.due_fees = installment_line.outstanding_fees
                                                else:
                                                    installment_line.due_fees = 0.0
                                                tax_paid = True
                                                main_amt = 0.0
                                                break 
                                            
                        if not main_amt:
                            if not late_fee:
                                break_loop = True
                            break
                        
                        
            if installment_line.late_fee and installment_line.late_fee > 0.0:
                if not late_fee:
                    continue
                for type_line in search_ids:
                    if type_line.type == 'late_fee':
                        if not type_line.gl_code:
                            raise UserError(_('Please Configure GLCode For fees Amount'))
                        for fees_line in installment_line.fee_lines:
                            fees_dict = {}
                            interest_dict = {}
                            if fees_line.product_id.id == type_line.product_id.id and fees_line.is_paid == False:
                                fees_line_base = round(fees_line.base - fees_line.base_paid, 2)
                                fees_line_tax = round(fees_line.tax - fees_line.tax_paid,2)
                                if fees_line_base > 0.0 and late_fee >= fees_line_base + fees_line_tax:
                                    total_paid_amount = 0
                                    if type_line.tax_id:
                                        rm_tx = self.get_tax_value(type_line.tax_id, fees_line_base)
                                        fees_line_tax = fees_line_base - rm_tx
                                        fees_line_base = fees_line_base - fees_line_tax
                                    if fees_line_base:
                                        base_amt = fees_line_base
                                        if currency_id.id != company_curren.id:
                                            amount_currency = base_amt
                                            amount = company_curren.with_context(date=date_new).compute(base_amt, currency_id)
                                        else:
                                            amount_currency = False
                                        if not amount_currency:
                                            fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':base_amt})
                                        else:
                                            fees_dict.update({'partner_id':self.loan_id.partner_id.id,\
                                                              'account_id':type_line.gl_code.id,\
                                                              'debit':0.0, 'credit':amount, 'amount_currency':-amount_currency,\
                                                               'currency_id':currency_id.id})
#                                         installment_line.with_context({'fee':fees_dict.get('credit')}).onchange_fees()
                                        total_paid_amount = total_paid_amount + base_amt
                                    if type_line.tax_id:
                                        tx_tot = fees_line_tax
                                        if currency_id.id != company_curren.id:
                                            amount_currency = tx_tot
                                            amount = company_curren.with_context(date=date_new).compute(tx_tot, currency_id)
                                        else:
                                            amount_currency = False
                                        if not amount_currency:
                                            interest_dict = self.get_interest_vals(tx_tot, type_line.tax_id.account_id)
                                        else:
                                            interest_dict.update({'partner_id':self.loan_id.partner_id.id,\
                                                                'account_id':type_line.tax_id.account_id.id,\
                                                                'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                               'currency_id':currency_id.id})
#                                         if interest_dict :
#                                             installment_line.with_context({'int':interest_dict.get('credit')}).onchange_interest()
                                        total_paid_amount = total_paid_amount + tx_tot
                                        installment_line.paid_late_fee_tx = tx_tot
                                         
#                                     fees_line.write({'base_paid':base_amt + fees_line.base_paid, 'tax_paid':fees_line_tax + fees_line.tax_paid, 'is_paid':True})
                                    fees_line.write({'base_paid':base_amt + fees_line.base_paid + fees_line_tax, 'is_paid':True})
                                    if fees_dict:
                                            list_mv_line.append((0, 0, fees_dict))
                                    if interest_dict:
                                        list_mv_line.append((0, 0, interest_dict))
                                    if fees_line_tax:
                                        late_fee = late_fee - (fees_line_base + fees_line_tax)
                                    else:
                                        late_fee = late_fee - fees_line_base 
                                         
                                    installment_line.late_fee = installment_line.late_fee - total_paid_amount
                                    installment_line.paid_late_fee = base_amt
                                    if late_fee:
                                        break_loop = False
                                    else:
                                        if not main_amt:
                                            break_loop = True
                                            break
                                     
                                else:
                                    if late_fee >= fees_line_base:
                                        total_paid_amount = 0
                                        base_amt = fees_line_base
                                        base_paid = False
                                        tax_paid = False
                                        if fees_line_base:
                                            if currency_id.id != company_curren.id:
                                                amount_currency = fees_line_base
                                                amount = company_curren.with_context(date=date_new).compute(fees_line_base, currency_id)
                                            else:
                                                amount_currency = False
                                            if not amount_currency:
                                                fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':fees_line_base})
                                            else:
                                                fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,\
                                                                  'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                                  'currency_id':currency_id.id})
#                                             installment_line.with_context({'fee':fees_dict.get('credit')}).onchange_fees()
                                    #                                             total_paid_amount = total_paid_amount + fees_line_base
                                            list_mv_line.append((0, 0, fees_dict))
                                            base_paid = True
                                            installment_line.late_fee = installment_line.late_fee - fees_line_base
                                            installment_line.paid_late_fee = fees_line_base
                                            fees_line.write({'base_paid':fees_line_base  + fees_line.base_paid})
                                            late_fee = round(late_fee,2)
                                            rem = late_fee - fees_line_base
                                            late_fee = rem
                                        if late_fee >=fees_line_tax:
                                            ## new changes done hereesssssss for payment calculation ......
                                            tx_amt = 0.0
                                            if type_line.tax_id:
                                                tx_amt = fees_line_tax
                                                if tx_amt:
                                                    fees_dict_tx = {}
                                                    fees_line_tax = fees_line_tax - tx_amt
                                                    if currency_id.id != company_curren.id:
                                                        amount_currency = tx_amt
                                                        amount = company_curren.with_context(date=date_new).compute(tx_amt, currency_id)
                                                    else:
                                                        amount_currency = False
                                                    if not amount_currency:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':tx_amt})
                                                    else:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,\
                                                                          'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                                          'currency_id':currency_id.id})
    #                                                 installment_line.with_context({'fee':fees_dict_tx.get('credit')}).onchange_fees()
                                    #                                                     total_paid_amount = total_paid_amount + tx_amt
                                                    list_mv_line.append((0, 0, fees_dict_tx))
                                                    installment_line.late_fee = installment_line.late_fee - tx_amt
                                                    fees_line.write({'tax_paid':tx_amt  + fees_line.tax_paid})
                                                    installment_line.paid_late_fee = tx_amt
                                                    tax_paid = True
                                                    late_fee = round(late_fee,2)
                                                    rem = late_fee - tx_amt
                                                    late_fee = rem
                                        else:
                                            tx_amt = 0.0
                                            if type_line.tax_id:
                                                tx_amt = self.get_tax_value(type_line.tax_id, late_fee)
                                                tx_cal_amt = late_fee - tx_amt
                                                late_fee = late_fee - tx_cal_amt
                                                tx_amt = late_fee
                                                if tx_amt:
                                                    fees_dict_tx = {}
                                                    fees_line_tax = fees_line_tax - tx_amt
                                                    if currency_id.id != company_curren.id:
                                                        amount_currency = tx_amt
                                                        amount = company_curren.with_context(date=date_new).compute(tx_amt, currency_id)
                                                    else:
                                                        amount_currency = False
                                                    if not amount_currency:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':tx_amt})
                                                    else:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,\
                                                                          'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                                          'currency_id':currency_id.id})
                                                    installment_line.with_context({'fee':fees_dict_tx.get('credit')}).onchange_fees()
                                    #                                                     total_paid_amount = total_paid_amount + tx_amt
                                                    list_mv_line.append((0, 0, fees_dict_tx))
                                                    fees_line.write({'tax_paid':tx_amt  + fees_line.tax_paid})
                                                    installment_line.outstanding_fees = installment_line.outstanding_fees - tx_amt
                                                    installment_line.paid_fees_tx = tx_amt
                                                    # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                                    if installment_line.date <= today:
                                                        installment_line.due_fees = installment_line.outstanding_fees
                                                    else:
                                                        installment_line.due_fees = 0.0
                                    #                                                     fees_line.write({'tax_paid':rem + fees_line.tax_paid})
                                                    if not fees_line_tax:
                                                        tax_paid = True
                                                    late_fee = 0.0
                                           
                                        if not fees_line_base:
                                            base_paid = True
                                        if base_paid and tax_paid: fees_line.is_paid = True
                                        if not late_fee:
                                            if not main_amt:
                                                break_loop = True
                                                break
                                         
                                    else:
                                        rem_fr_tx_amt = 0.0
                                        if late_fee > 0.0:
                                            total_paid_amount = 0
                                            late_fee = round(late_fee, 2)
                                            tx_amt = self.get_tax_value(type_line.tax_id, late_fee)
                                            tx_cal_amt = late_fee - tx_amt
                                            late_fee = late_fee - tx_cal_amt
                                            print (late_fee,'latessssssssssssssssss')
                                            if tx_cal_amt:
                                                rem_fr_tx_amt = tx_cal_amt
                                            if currency_id.id != company_curren.id:
                                                amount_currency = late_fee
                                                amount = company_curren.with_context(date=date_new).compute(late_fee, currency_id)
                                            else:
                                                amount_currency = False
                                            if not amount_currency:
                                                fees_dict.update({'partner_id':self.loan_id.partner_id.id,'account_id':type_line.gl_code.id,'debit':0.0, 'credit':late_fee})
                                            else:
                                                fees_dict.update({'partner_id':self.loan_id.partner_id.id,\
                                                                  'account_id':type_line.gl_code.id,'debit':0.0,\
                                                                'credit':amount,'amount_currency':-amount_currency,'currency_id':currency_id.id})
                                            
                                            
#                                             total_paid_amount = total_paid_amount + late_fee
                                            installment_line.late_fee = installment_line.late_fee - late_fee
                                            installment_line.paid_late_fee = late_fee
                                            list_mv_line.append((0, 0, fees_dict))
                                            fees_line.write({'base_paid':late_fee + fees_line.base_paid})
                                            late_fee = 0.0
                                            break_loop = True
                                            
                                            
                                            if rem_fr_tx_amt:
                                                tx_amt = rem_fr_tx_amt
                                                if tx_amt:
                                                    fees_dict_tx = {}
    #                                                 fees_line_tax = tx_amt
                                                    if currency_id.id != company_curren.id:
                                                        amount_currency = tx_amt
                                                        amount = company_curren.with_context(date=date_new).compute(tx_amt, currency_id)
                                                    else:
                                                        amount_currency = False
                                                    if type_line.tax_id:
                                                        gl_acc = type_line.tax_id.account_id.id
                                                    else:
                                                        gl_acc = type_line.gl_code.id
                                                    if not amount_currency:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,'debit':0.0, 'credit':tx_amt})
                                                    else:
                                                        fees_dict_tx.update({'partner_id':self.loan_id.partner_id.id,'account_id':gl_acc,\
                                                                          'debit':0.0, 'credit':amount,'amount_currency':-amount_currency,\
                                                                          'currency_id':currency_id.id})
                                                    installment_line.with_context({'fee':fees_dict_tx.get('credit')}).onchange_fees()
    #                                                     total_paid_amount = total_paid_amount + tx_amt
                                                    list_mv_line.append((0, 0, fees_dict_tx))
                                                    installment_line.late_fee = installment_line.late_fee - tx_amt
    #                                                 fees_line.write({'tax_paid':tx_amt  + fees_line.tax_paid})
                                                    fees_line.write({'base_paid':tx_amt  + fees_line.tax_paid + fees_line.base_paid})
                                                    installment_line.paid_fees_tx = tx_amt
                                                    # if datetime.datetime.strptime(installment_line.date, "%Y-%m-%d").date() <= today:
                                                    if installment_line.date <= today:
                                                        installment_line.due_fees = installment_line.late_fee
                                                    else:
                                                        installment_line.due_fees = 0.0
                                                    tax_paid = True
                                                    main_amt = 0.0
                                                    if not main_amt:
                                                        break 
                                        else:
                                            if not late_fee:
                                                if not main_amt:
                                                    break_loop = True
                                                    break
#                                             if not main_amt:
#                                                 break
                                        
#                         if not main_amt:
#                             break_loop = True
#                             break
                         
                    #==========================for late fees====================
                
                   
            if not installment_line.outstanding_prin and not installment_line.outstanding_int and not installment_line.outstanding_fees and not installment_line.late_fee:
                installment_line.state = 'paid'
            else:
                installment_line.state = 'open'
        if main_amt:
            if not self.loan_id.loan_type.account_id:
                raise Warning(_("Please Define Excess Payment Account"))
            excess_lines = self.get_extra_payment(main_amt, self.loan_id, date_new, self.loan_id.loan_type.account_id, currency_id, company_curren)
            if excess_lines:                
                list_mv_line.append((0, 0, excess_lines))
            print (main_amt,'Extra Amount================')
            print ("To Do For Customer pay extra Payment") 
                               
        print (list_mv_line,'list_of idct')
        move_vals.update({'line_ids':list_mv_line})
        move_id = self.env['account.move'].create(move_vals)
        if move_id:
            move_id.post()
            for l in affected_line_list:
                
                vals = {}
                fees_amt = 0.0
                late_fee_amt = 0.0
                fees_amt = l.paid_fees + l.paid_fees_tx
                late_fee_amt = l.paid_late_fee + l.paid_late_fee_tx
                vals.update({'pay_date':date_new, 'prin_amt':l.paid_prin,\
                             'int_amt':l.paid_int,'fees_amt':fees_amt,\
                             'late_fee_amt':late_fee_amt,'base_late_fee_amt':l.paid_late_fee ,\
                             'base_late_fee_amt_tx':l.paid_late_fee_tx,\
                             'move_id':move_id.id,\
                             'base_fee_paid':l.paid_fees,'base_fee_tax_paid':l.paid_fees_tx,\
                            'line_id':l.id,'state':'draft'})
                if vals:
                    self.env['payment.details'].create(vals)
                    l.paid_prin = 0.0
                    l.paid_int = 0.0
                    l.paid_fees = 0.0
                    l.paid_fees_tx = 0.0
                    l.paid_late_fee = 0.0
                    l.paid_late_fee_tx = 0.0
                l.move_id = move_id.id
            return move_id
        
        
        
            
    def get_extra_payment(self, main_amt, loan_id, date_new, account_id, currency_id, company_curren):
        move_lines_extra_payemnt = {}
        
        if currency_id.id != company_curren.id:
            amount_currency = main_amt
            amount = company_curren.with_context(date=date_new).compute(main_amt, currency_id)
        else:
            amount_currency = False
        if not amount_currency:
            move_lines_extra_payemnt.update({
                    'account_id':account_id.id,
                    'name':"Excess Payment",
                    'credit':main_amt,
                    'debit':0.0,
                    'partner_id':loan_id.partner_id.id,
                    })
        else:
            move_lines_extra_payemnt.update({
                    'account_id':account_id.id,
                    'name':"Excess Payment",
                    'credit':amount,
                    'debit':0.0,
                    'partner_id':loan_id.partner_id.id,
                    'amount_currency':-amount_currency,
                    'currency_id':currency_id.id
                    })
        return move_lines_extra_payemnt
        
        