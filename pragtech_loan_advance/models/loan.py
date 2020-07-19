import time
import datetime
from odoo.osv import osv
from odoo import fields, models, api, _
from datetime import date
import math
from odoo import exceptions, _
from odoo.exceptions import UserError, ValidationError, Warning 
from odoo.tools.safe_eval import safe_eval
from dateutil.relativedelta import relativedelta

class LoanCustomer(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    incom = fields.Float('Monthly Incom', digits=(12, 2))
    is_group = fields.Boolean(string='Is Group',store=True)
    
class LoanPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _inherit = 'res.partner.bank'
    account_id = fields.Many2one('account.account', 'Account')
    
class PartnerLine(models.Model):
    _name = 'res.partner.loan.line'
    _description = 'Partner Loan Line'
    
    name = fields.Many2one('res.partner')
    loan_id = fields.Many2one('account.loan')

class CollateralType(models.Model):
    _name = 'collateral.type'
    _description = 'Collateral Type'
    
    name = fields.Char('Collateral Type')
    
class CollateralLine(models.Model):
    _name = 'collateral.line'
    _description = 'Collateral line'
    
    loan_id = fields.Many2one('account.loan')
    type_id = fields.Many2one('collateral.type','Collateral Type')
    value = fields.Float('Collateral Value')
    last_date = fields.Date('Collateral Last Valuation Date')
    expiry_date = fields.Date('Collateral Expiry Date')
    is_registered = fields.Boolean('Is Registered with RBD')
    partner_id = fields.Many2one(related='loan_id.partner_id', string='Customer Name',store=True)
    
class AccountLoan(models.Model):

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        state_obj = self.env['loan.stages'].search([('sequence', '=', 1)], limit=1)
        if not state_obj:
            return False
        return state_obj.id

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for task in self:
            if task.kanban_state == 'normal':
                task.kanban_state_label = task.legend_normal
            elif task.kanban_state == 'blocked':
                task.kanban_state_label = task.legend_blocked
            else:
                task.kanban_state_label = task.legend_done

    stage_id = fields.Many2one('loan.stages', string='Stage', group_expand='_read_group_stage_ids',
                               default=_get_default_stage_id, track_visibility='onchange', index=True, copy=False)
    color = fields.Integer(string='Color Index')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
    ], default='0', index=True, string="Priority")

    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True,
        help="A task's kanban state indicates special situations affecting it:\n"
             " * Grey is the default situation\n"
             " * Red indicates something is preventing the progress of this task\n"
             " * Green indicates the task is ready to be pulled to the next stage")
    kanban_state_label = fields.Char(compute='_compute_kanban_state_label', string='Kanban  State Label',
                                     track_visibility='onchange')
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked Explanation', readonly=True,
                                 related_sudo=False)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid Explanation', readonly=True,
                              related_sudo=False)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing Explanation', readonly=True,
                                related_sudo=False)

    @api.onchange('stage_id', 'state')
    def onchange_stage_id(self):
        if self._origin.id:
            record = self.env['account.loan'].browse(self._origin.id)
            if record.state != self.stage_id.state:
                raise Warning(_('Please Change To Appropriate State Before Moving To This Stage.'))

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env['loan.stages'].search([])


    @api.multi
    def _loan_period_get(self):
        obj = self.env['loan.installment.period']
        ids = obj.search([('name', 'ilike', '')])
        res = obj.read(['name', 'period'])
        return [(r['name'], r['name']) for r in res]

    @api.multi
    def _loan_type_get(self):
        obj = self.env['account.loan.loantype']
        ids = obj.search([('name', 'ilike', '')])
        res = obj.read(['name', 'calculation'])
        return [(r['name'], r['name']) for r in res]
    
    @api.multi
    def reset_values(self):
        self.write({
                      'emi_cal':0.0,'tot_amt':0,'flat_pa':0.0,\
                      'flat_pm':0.0,'tot_int_amt':0.0,'yr_int_amt':0.0,\
                      'flat_emi_cal':0.0,'flat_tot_amt':0.0,'flat_tot_int_amt':0.0,\
                      'flat_yr_int_amt':0.0  
            })
    
    
    
    def get_reducing(self, amt, mth, intr):
        try:
            k = 12
            i = intr / 100
            a = i / k or 0.00
            b = (1 - (1 / ((1 + (i / k)) ** mth))) or 0.00
            emi = ((amt * a) / b) or 0.00
            tot_amt = emi * mth
            tot_int_amt = tot_amt - amt
            yr_amt = (tot_int_amt * k) / mth
            flat_pa = (yr_amt * 100) / amt
            flat_pm = flat_pa / k
            self.write({'emi_cal':emi, 'tot_amt':tot_amt,\
                        'flat_pa':flat_pa, 'flat_pm':flat_pm,\
                        'tot_int_amt':tot_int_amt, 'yr_int_amt':yr_amt})
        except ZeroDivisionError:
            flat_pm = 0
            
            
    def convert_month_to_year(self, mth):
        if mth:
            return mth / 12
            
            
            
    def get_flat(self, amt, mth, intr):
        print ("calcuation for flat loan")
        year  = self.convert_month_to_year(mth)
        
        interest_amount = (amt * intr) / 100 
        if year:
            total_interest = interest_amount * year
            moth_int = (amt / mth) + (total_interest / mth) 
            total_amt_with_int = amt + total_interest
            year_int = total_interest / year
            self.write({'flat_tot_int_amt':total_interest,\
                        'flat_emi_cal':moth_int,'flat_tot_amt':total_amt_with_int,\
                        'flat_yr_int_amt':year_int,
                        })
        
        
    @api.multi
    def cal_amt(self): 
        read_obj = self.read()
        for read_id in read_obj:
            amt = read_id['loan_amt']
            mth = read_id['month']
            intr = read_id['int_rate'] 
            self.get_reducing(amt, mth, intr)
            self.get_flat(amt, mth, intr)
            
            
    @api.multi
    def re_set(self, vals):          
        self.write({'loan_amt':0.00, 'month':0, 'int_rate':0.00, 'emi_cal':0.00, 'tot_amt':0.00, 'flat_pa':0.00, 'flat_pm':0.00, 'tot_int_amt':0.00, 'yr_int_amt':0.00})                               
    
    @api.one
    @api.depends('apply_date', 'total_installment', 'loan_amount', 'loan_type')
    def compute_loan_interest(self):
        res = {}
        for loan in self:
            res[loan.id] = {
                'interest_rate': 0.0,
            }
            rate = 0.0
            
            for int_version in loan.loan_type.interestversion_ids:
                if int_version.start_date and int_version.end_date:
                    if loan.apply_date >= int_version.start_date and loan.apply_date <= int_version.end_date:
                        date_check = 1
                    else:
                        date_check = 0
                elif int_version.start_date:

                    if loan.apply_date >= int_version.start_date:
                        date_check = 1
                    else:
                        date_check = 0
                elif int_version.end_date:

                    if loan.apply_date <= int_version.end_date:
                        date_check = 1
                    else:
                        date_check = 0
                else:
                    date_check = 1
                if date_check:
                    for int_version_line in int_version.interestversionline_ids:
                        if int_version_line.min_month and int_version_line.max_month:

                            if loan.total_installment >= int_version_line.min_month and loan.total_installment <= int_version_line.max_month:
                                month_check = 1
                            else:
                                month_check = 0
                        elif int_version_line.min_month:

                            if loan.total_installment >= int_version_line.min_month:
                                month_check = 1
                            else:
                                month_check = 0
                        elif int_version_line.max_month:

                            if loan.total_installment <= int_version_line.max_month:
                                month_check = 1
                            else:
                                month_check = 0
                        else:
                            month_check = 1
                        if month_check:
                            if int_version_line.min_amount and int_version_line.max_amount:
                                if loan.loan_amount >= int_version_line.min_amount and loan.loan_amount <= int_version_line.max_amount:
                                    rate = int_version_line.rate
                                    break
                            elif int_version_line.min_amount:
    
                                if loan.loan_amount >= int_version_line.min_amount:
                                    rate = int_version_line.rate
                                    break
                            elif int_version_line.max_amount:
    
                                if loan.loan_amount <= int_version_line.max_amount:
                                    rate = int_version_line.rate
                                    break
                            else:
                                rate = int_version_line.rate
                                break
                        
                date_check = 0
                month_check = 0
            loan.interest_rate = rate
    
#     def compute_loan_interest(self, cr, uid, ids, field_name, arg, context=None):
#         res = {}
#         for loan in self.browse(cr, uid, ids):
#             res[loan.id] = {
#                 'interest_rate': 0.0,
#             }
#             rate = 0.0
#             for int_version in loan.loan_type.interestversion_ids:
#                 if loan.apply_date >= int_version.start_date and loan.apply_date <= int_version.end_date:
#                     for int_version_line in int_version.interestversionline_ids:
#                         if loan.total_installment >= int_version_line.min_month and loan.total_installment <= int_version_line.max_month and \
#                              loan.loan_amount >= int_version_line.min_amount and loan.loan_amount <= int_version_line.max_amount:
#                     
#                             rate = int_version_line.rate
#             res[loan.id]['interest_rate'] = rate
#         return res
    
    def _compute_payment(self):
        for ele in self:
            cur_id = None
            if ele.journal_disburse_id:
                if ele.journal_disburse_id.currency_id:
                    cur_id = ele.journal_disburse_id.currency_id
                else:
                    cur_id = ele.journal_disburse_id.company_id.currency_id
                    
            paid_capital = 0
            paid_interest = 0
            paid_fee = 0
            for line in ele.installment_id:
                paid_line = self.env['payment.details'].search([('line_id','=',line.id),('state','!=','cancel')])
                for o in paid_line:
                    paid_capital += o.prin_amt
                    paid_interest += o.int_amt
                    paid_fee += o.fees_amt

            if cur_id and (cur_id.id != ele.company_id.currency_id.id):
#             if cur_id.id != o.move_id.currency_id.id:
                paid_capital = ele.company_id.currency_id.with_context(date=datetime.datetime.now()).compute(paid_capital, cur_id)
                paid_interest = ele.company_id.currency_id.with_context(date=datetime.datetime.now()).compute(paid_interest, cur_id)
                paid_fee = ele.company_id.currency_id.with_context(date=datetime.datetime.now()).compute(paid_fee, cur_id)
                    
            ele.total_payment = paid_capital + paid_interest + paid_fee
            ele.total_principal_paid = paid_capital
            ele.total_interest_paid = paid_interest
            ele.total_fees_paid = paid_fee
            
    
#     def _compute_total_payment(self):
#         for ele in self:
#             for payment in ele.repayment_details: 
#                 if payment.release_number.state == 'posted':
#                     ele.total_payment += payment.amt
#     
#     def _compute_total_principle_paid(self):
#         for ele in self:
#             prin_paid = 0
#             prin_total = 0
#             for line in ele.installment_id:
#                 prin_paid += line.outstanding_prin
#                 prin_total += line.capital
#                 
#             ele.total_principle_paid = prin_total - prin_paid
#     
#     def _compute_total_interest_paid(self):
#         for ele in self:
#             int_paid = 0
#             int_total = 0
#             for line in ele.installment_id:
#                 int_paid += line.outstanding_int
#                 int_total += line.interest
#                 
#             ele.total_interest_paid = int_total - int_paid
#         
#     def _compute_total_fees_paid(self):
#         for ele in self:
#             fees_paid = 0
#             fees_total = 0
#             for line in ele.installment_id:
#                 fees_paid += line.outstanding_fees
#                 fees_total += line.fees
#             ele.total_fees_paid = fees_total - fees_paid
        
#     def _compute_total_late_fees_paid(self):
#         for ele in self:
#             total = prin = inte = fees = 0.0
#             int_paid = int_total = 0
#             prin_paid = prin_total = 0
#             fees_paid = fees_total = 0
#             for payment in ele.repayment_details: 
#                 if payment.release_number.state == 'posted':
#                     total += payment.amt
#             for line in ele.installment_id:
#                 prin_paid += line.outstanding_prin
#                 prin_total += line.capital
#             prin = prin_total - prin_paid  
#             for line in ele.installment_id:
#                 int_paid += line.outstanding_int
#                 int_total += line.interest
#             inte = int_total - int_paid
#             for line in ele.installment_id:
#                 fees_paid += line.outstanding_fees
#                 fees_total += line.fees
#             fees = fees_total - fees_paid
#             ele.total_late_fees_paid = round(total,2) - (round(prin,2) + round(inte,2) + round(fees,2))
            
            
    _name = 'account.loan'
    description = 'Account Loan'
    
    _inherit = ['mail.thread']
    
    _order = 'id desc'
    _rec_name = 'loan_id'

    lead_id = fields.Many2one('crm.lead', 'Lead')

    id = fields.Integer('ID', readonly=True, track_visibility='always')
    loan_id = fields.Char('Loan Id', size=32, readonly=True, track_visibility='onchange')
    proof_id = fields.One2many('account.loan.proof', 'loan_id', 'Proof Detail')
#     auto_id = fields.Integer('Auto Id', size=32, default=lambda self: self.env['ir.sequence'].next_by_code('loan.id'), track_visibility='onchange')
    name = fields.Char('Purpose', size=128, required=True, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', 'Customer', required=True,track_visibility='onchange')
    proof_1 = fields.Many2one('res.partner', 'Guarantor/Co-Signer 1', track_visibility='onchange')
    proof_2 = fields.Many2one('res.partner', 'Guarantor/Co-Signer 2', track_visibility='onchange')
    loan_type = fields.Many2one('account.loan.loantype', 'Loan Type', required=True, track_visibility='onchange')
#         'loan_type':fields.selection(_loan_type_get,'Loan Type', size=32 ,select=True, required=True),
#         'loan_period':fields.selection(_loan_period_get,'Loan Period',select=True, required=True),
    loan_period = fields.Many2one('loan.installment.period', 'Loan Period', required=True, track_visibility='onchange')
    loan_amount = fields.Float('Account Loan Amount', digits=(12, 2), required=True, states={'draft':[('readonly', False)]}, track_visibility='onchange')
    approve_amount = fields.Float('Disbursement Amount', digits=(12, 2), readonly=True, track_visibility='onchange')
    process_fee = fields.Float('Processing Fee', digits=(12, 2), track_visibility='onchange')
    total_installment = fields.Integer('Total Installment', readonly=False, required=True, default=0.0, track_visibility='onchange')
#         'interest_rate': fields.float('Interest Rate',digits=(10,2),readonly=True,required=True,),
    interest_rate = fields.Float(compute='compute_loan_interest', string='Interest Rate (%)', store=True, track_visibility='onchange')
    
#   'interest_rate': fields.function(compute_loan_interest,string='Interest Rate', track_visibility='always',multi='all',store=True),
    
    department =fields.Selection([('mbs','Micro Business Solutions'),('sme','SME Growth')],string="Department")
    is_refugee = fields.Selection([('ref','Refugee'),('non_ref','Non Refugee')])
    
    
    apply_date = fields.Date('Apply Date', states={'draft':[('readonly', False)]}, default=time.strftime('%Y-%m-%d'),track_visibility='onchange')
    approve_date = fields.Date('Approve Date', readonly=False, track_visibility='onchange')
    cheque_ids = fields.One2many('account.loan.bank.cheque', 'loan_id', 'Cheque Detail', track_visibility='onchange')
    state = fields.Selection([
       ('draft', 'Application Review'),
       ('apply', 'Application Approved'),
       ('partial', 'Partially Disbursed'),
       ('approved', 'Disbursed'),
       ('done', 'Closed'),
       ('cancel', 'Declined'),
    ], 'State', readonly=True, index=True, default='draft', track_visibility='onchange')
    return_type = fields.Selection([
       ('cash', 'By Cash'),
       ('cheque', 'By Cheque'),
       ('automatic', 'Electronic Clearing'),
    ], 'Payment Type', index=True, default='automatic', track_visibility='onchange')
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', required=False, readonly=True, states={'draft':[('readonly', False)]},track_visibility='onchange')
#     running_loan = fields.Many2many('account.loan', 'account_loan_running', 'loan_id', 'auto_id', 'Current Loans',track_visibility='onchange')
    installment_id = fields.One2many('account.loan.installment', 'loan_id', 'Installments', track_visibility='onchange')
    interest = fields.Float('Interest', digits=(12, 2),track_visibility='onchange', copy=False)
    voucher_id = fields.Many2one('account.voucher', 'Voucher', readonly=True, track_visibility='onchange')
    notes = fields.Text('Description', track_visibility='onchange')

    cus_pay_acc = fields.Many2one('account.account', method=True, string="Customer Loan Account", company_dependent=True,  track_visibility='onchange')
    int_acc = fields.Many2one('account.account', method=True, string="Interest Account", company_dependent=True,  track_visibility='onchange')
    bank_acc = fields.Many2one('account.account', method=True, string="Bank Account", company_dependent=True,  track_visibility='onchange')
    proc_fee = fields.Many2one('account.account', method=True, string="Processing Fee Account", company_dependent=True,  track_visibility='onchange')
    anal_acc = fields.Many2one('account.analytic.account', method=True, string="Analytic Account", company_dependent=True, help="This analytic account will be used", track_visibility='onchange')

    move_id = fields.One2many('account.move.line', 'acc_loan_id', 'Move Line', readonly=True, track_visibility='onchange')  
    
    loan_amt = fields.Float('Amount ', digits=(12, 2), required=True, track_visibility='onchange')
    req_amt = fields.Float('Amount of Loan Required', digits=(12, 2))
    
    month = fields.Integer('Loan Tenure (Months)', track_visibility='onchange')
    int_rate = fields.Float('Interest Rate', digits=(12, 2), default=1, track_visibility='onchange')
    emi_cal = fields.Float('Calculated Monthly EMI', readonly=True)
    tot_amt = fields.Float('Total Amount with Interest', readonly=True)
    flat_pa = fields.Float('Flat Interest Rate PA', readonly=True)
    flat_pm = fields.Float('Flat Interest Rate PM', readonly=True)
    tot_int_amt = fields.Float('Total Interest Amount', readonly=True)
    yr_int_amt = fields.Float('Yearly Interest Amount', readonly=True)   
    
    flat_emi_cal = fields.Float('Calculated FLat Monthly  EMI', readonly=True)
    flat_tot_amt = fields.Float('Total Flat Amount with  Interest', readonly=True)
    flat_pa1 = fields.Float('Flat Interest Rate PA1', readonly=True)
    flat_pm1 = fields.Float('Flat Interest Rate  PM1', readonly=True)
    flat_tot_int_amt = fields.Float('Total Flat Interest  Amount', readonly=True)
    flat_yr_int_amt = fields.Float('Yearly Flat Interest  Amount', readonly=True)
    bank_id = fields.Many2one("res.partner.bank", string = "Customer Bank")      
    
    disbursement_details = fields.One2many("account.loan.disbursement",'loan_id',readonly=True)
    old_disburse_amt = fields.Float("Remain amt")
    journal_disburse_id = fields.Many2one('account.journal', "Disbursement Journal")
    journal_repayment_id = fields.Many2one('account.journal', "Repayment Journal")
    payment_freq = fields.Selection([('daily','Daily'),('weekly','Weekly'),('bi_month','Bi Monthly'),('monthly','Monthly'), ('quarterly','Quarterly'), ('half_yearly','Half-Yearly'),('yearly','Yearly')], "Payment Frequency", default="monthly")
    payment_schedule_ids = fields.One2many('payment.schedule.line', 'loan_id', 'Payment Schedule', track_visibility='onchange')
    
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('account.loan'))
    group_members = fields.One2many('res.partner.loan.line','loan_id','Group Members')
    is_group = fields.Boolean(related="partner_id.is_group",store=True)
    is_collateral = fields.Boolean(default=False)
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    date_done = fields.Date('Date Done',readonly=True)
    collateral_lines = fields.One2many('collateral.line','loan_id','Collateral Lines')
    
    repayment_details = fields.One2many("account.loan.repayment",'loan_id',readonly=True)
    repayment_basis = fields.Selection([('disbursed_amt','Disbursed Amount'), ('sanctioned_amt','Sanctioned Amount')], "Repayment Basis", default="sanctioned_amt")
    grace_period = fields.Integer("Grace Period (Days)")
    classification = fields.Char(string="Classification")
    interest_type = fields.Selection(related="loan_type.calculation", string='Interest Type', readonly=True, store=True, track_visibility='onchange')
    city = fields.Char(related='partner_id.city', string='City', store=True)
    
    
    total_payment = fields.Float(compute='_compute_payment')
    total_principal_paid = fields.Float(compute='_compute_payment')
    total_interest_paid = fields.Float(compute='_compute_payment')
    total_fees_paid = fields.Float(compute='_compute_payment')
#     total_late_fees_paid = fields.Float(compute='_compute_total_late_fees_paid')


    @api.model
    def create(self, vals):
        vals['loan_id'] = self.env['ir.sequence'].next_by_code('loan.number')
        res = super(AccountLoan, self).create(vals)
        template = self.env.ref('pragtech_loan_advance.email_template_loan_creation')
        mail_obj = self.env['mail.template'].browse(template.id)
        if res.message_follower_ids and res.message_follower_ids[0].partner_id:
            
            for user in res.message_follower_ids:
                if not user.id == res.partner_id.id: 
                    mail_obj.partner_to = user.id
                    mail_obj.sudo().send_mail(res.id)
        return res  
     
    @api.onchange('partner_id')    
    def onchange_partner_id(self):
        
        bank_ids = []
        if not self.partner_id:
            return {'value':{'contact': False, 'bank_id':False}}
        addr = self.env['res.partner'].address_get(['default', 'invoice'])
        ptr_bank_ids = self.env['res.partner.bank'].search([('partner_id', '=', self.partner_id.id)])
        for bnk_id in ptr_bank_ids:
            bank_ids.append(bnk_id.id)
        
        return {'value':{'contact': addr['default']}, 'domain':{'bank_id':[('id', 'in', bank_ids)]}}

    @api.onchange('loan_period')
    def onchange_loan_period(self):
        res = {}
        if self.loan_period:
            res = {'total_installment': self.loan_period.period}
        return {'value':res}
    
    
    @api.onchange('loan_amount')
    def onchange_loan_amount(self):
        res = {}
        if self.loan_amount:
            res = {'loan_amt': self.loan_amount}
        return {'value':res}
    
    @api.onchange('total_installment')
    def onchange_total_installment(self):
        res = {}
        if self.total_installment:
            res = {'month': self.total_installment}
        return {'value':res}
    
    @api.onchange('interest_rate')
    def onchange_interest_rate(self):
        res = {}
        if self.interest_rate:
            res = {'int_rate': self.interest_rate}
        return {'value':res}
    
    
    @api.onchange('apply_date', 'total_installment', 'loan_amount', 'loan_type')
    def onchange_loan_type(self):
        date_check = 0
        month_check = 0
        amount_check = 0
        
        
        res = {}
        if not self.apply_date:
            return False
        if not self.total_installment:
            return False
        if not self.loan_amount:
            return False
        if not self.loan_type:
            return False
        if self.loan_type:
#             loan_type = self.env['account.loan.loantype'].browse()
            rate = 0.0
            for int_version in self.loan_type.interestversion_ids:
                if int_version.start_date and int_version.end_date:
                    if self.apply_date >= int_version.start_date and self.apply_date <= int_version.end_date:
                        date_check = 1
                    else:
                        date_check = 0
                elif int_version.start_date:

                    if self.apply_date >= int_version.start_date:
                        date_check = 1
                    else:
                        date_check = 0
                elif int_version.end_date:

                    if self.apply_date <= int_version.end_date:
                        date_check = 1
                    else:
                        date_check = 0
                else:
                    date_check = 1
                if date_check:
                    for int_version_line in int_version.interestversionline_ids:
                        if int_version_line.min_month and int_version_line.max_month:
                            if self.total_installment >= int_version_line.min_month and self.total_installment <= int_version_line.max_month:
                                month_check = 1
                            else:
                                month_check = 0
                        elif int_version_line.min_month:
                            if self.total_installment >= int_version_line.min_month:
                                month_check = 1
                            else:
                                month_check = 0
                        elif int_version_line.max_month:
                            if self.total_installment <= int_version_line.max_month:
                                month_check = 1
                            else:
                                month_check = 0
                        else:
                            month_check = 1
#                 if month_check:
#                     for int_version_line in int_version.interestversionline_ids:
                        if month_check:
                            if int_version_line.min_amount and int_version_line.max_amount:
                                if self.loan_amount >= int_version_line.min_amount and self.loan_amount <= int_version_line.max_amount:
                                    rate = int_version_line.rate
                                    break
                            elif int_version_line.min_amount:
                                if self.loan_amount >= int_version_line.min_amount:
                                    rate = int_version_line.rate
                                    break
                            elif int_version_line.max_amount:
                                if self.loan_amount <= int_version_line.max_amount:
                                    rate = int_version_line.rate
                                    break
                            else:
                                rate = int_version_line.rate
                                break
                date_check = 0
                month_check = 0
                
            if not rate:
                raise exceptions.except_orm(_('Information Required'), _('Interest Rate is Not Defined.'))
            res = {'interest_rate': rate}
        return {'value':res}
    
    @api.multi
    def loan_interest_get(self):
        for loan in self:
            self.write({'approve_amount':loan.loan_amount - loan.process_fee, 'approve_date':time.strftime('%Y/%m/%d')})
        return True
                
    def calculate_eir(self, e, t, n, i, o):
        r = float(i) / float(12 * n)
        
        a = float(e) / 100 * float(i) / 12
        
        s = r + a
        
        t = s
        
        o = s * n * 12
        
        l = float(e) / 100 / 12
        
        c = 1 + l
        
        d = -float(12 * n)
        
        u = d - 1
        
        h = s * math.pow(c, d)
        
        f = l * float(i)
        
        p = s - h - f
        
        m = float(12 * n) * s * math.pow(c, u) - float(i)
        
        g = l - p / m
        
        for v  in range(0, 7):
            y = g * float(i)
            E = g
            b = 1 + E
            T = s - s * math.pow(b, d) - y
            C = float(12 * n) * s * math.pow(b, u) - float(i)
            D = g - T / C
            g = D
        
        I = 12 * g * 100
        return I
    ## total calculatin of tax for fee calculation in installment ................
    def get_tax_total(self, tx_ids, amount):
        tax_amt = 0.0
        for tx in tx_ids:
            if tx.amount:
                if not tx.price_include:
                    tax = (amount * tx.amount) / 100
                    tax_amt = tax_amt + tax
                    
            else:
                tax = round(amount - ((amount * 100) / (100 + tx.amount)),2)
                tax_amt = tax_amt + tax
        return tax_amt
    
    ## late fee tax calculations .........................
    def get_late_fee_tax_total(self, tx_ids, amount):
        tax_amt = 0.0
        dict_include_tx = {}
        for tx in tx_ids:
            if tx.amount:
                if not tx.price_include:
                    tax = (amount * tx.amount) / 100
                    tax_amt = tax_amt + tax
                else:
                    tax = (amount) - (amount * 100) / (100 + tx.amount) 
                    tax_amt = tax_amt + tax
                    if tax_amt:
                        dict_include_tx.update({'include':tax_amt})
                    
            else:
                tax = round(amount - ((amount * 100) / (100 + tx.amount)),2)
                tax_amt = tax_amt + tax
                
        if dict_include_tx:
            return dict_include_tx
        
        return tax_amt
        
    
    ## total calculatin of tax for fee calculation in installment ................
    def get_tax_total_incl_exl(self, tx_ids, amount):
        tax_amt = 0.0
        for tx in tx_ids:
            if tx.amount:
                if not tx.price_include:
                    tax = (amount * tx.amount) / 100
                    tax_amt = round(tax_amt + tax, 2)
                else:
                    tax = (amount) - (amount * 100) / (100 + tx.amount) 
                    tax_amt = round(tax_amt + tax,2)
            else:
                tax = round(amount - ((amount * 100) / (100 + tx.amount)),2)
                tax_amt = tax_amt + tax
        return tax_amt
        
    ##getting fees values basis of principle, interest and fees products ................
    def _get_fees_amount(self, loan_type, approve_amt, interest_amt):
        amt = 0.0
        if not loan_type.loan_component_ids:
            return amt
        is_exist = []
        sum_amt = 0.0
        sum_amt1 = 0.0
        
        flag = False
        flag1 = False
        global_list = []
        principal_list = []
        interest_list = []
        sum_amt_with_tax = 0.0
        global_add1 = 0.0
        global_add2 = 0.0
        global_add3 = 0.0
        global_add4 = 0.0
        fees_list = []
        global_dict = {}
        internal_dict = {}
        for line in loan_type.loan_component_ids:
            if line.type == 'principal':
                flag = True
                if line.product_id.id not in principal_list:
                    principal_list.append(line.product_id.id)
            if line.type == 'int_rate':
                flag1 = True
                if line.product_id.id not in interest_list:
                    global_list.append(line.product_id.id)
                    interest_list.append(line.product_id.id)
            if line.type == 'fees':
                if line.product_id.id not in fees_list:
                    global_list.append(line.product_id.id)
                    fees_list.append(line.product_id.id)
                    global_dict.update({line.product_id.id:line})
                    
                
        for line in loan_type.loan_component_ids:
            if line.type == 'fees':
                tx_tot = 0.0
                if line.amount_select == 'percentage':
                    for product in line.amount_percentage_base:
                        sum_amt = 0.0
                        if product.id in principal_list: 
                            if line.amount_percentage and flag:
                                percent = line.amount_percentage * line.quantity
                                amt = (approve_amt * percent) / 100
                                sum_amt = sum_amt + amt
#                                 for tx_line in line.tax_id:
                                if line.tax_id:
                                    tx_tot = self.get_tax_total(line.tax_id, sum_amt)
                                if tx_tot:
                                    line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                                    sum_amt = sum_amt + tx_tot
                                    line.write({'outstanding_product_amt':sum_amt})
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    internal_dict.update({line.product_id.id : sum_amt})
                                else:
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                                    internal_dict.update({line.product_id.id : sum_amt})
                                global_add1 = global_add1 + sum_amt
                                sum_amt = 0
                            
                        elif product.id in interest_list:
                            if line.amount_percentage and flag1:
                                percent = line.amount_percentage * line.quantity
                                amt1 = (interest_amt * line.amount_percentage) / 100
                                sum_amt = sum_amt + amt1
#                                 for tx_line in line.tax_id:
#                                     if tx_line.amount:
#                                         tx_tot = self.get_tax_total(tx_line, sum_amt)
                                if line.tax_id:
                                    tx_tot = self.get_tax_total(line.tax_id, sum_amt)
                                if tx_tot:
                                    line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                                    sum_amt = sum_amt + tx_tot
                                    line.write({'outstanding_product_amt':sum_amt})
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    internal_dict.update({line.product_id.id : sum_amt})
                                else:
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                                    internal_dict.update({line.product_id.id : sum_amt})
                                global_add2 = global_add2 + sum_amt
                                sum_amt = 0
                                
                        elif product.id in global_dict:
                            amt_tot = 0.0
                            for o in global_dict[product.id]:
                                if o.amount_select == 'percentage':
#                                     for f in o.amount_percentage_base:
                                    if o.product_id.id in internal_dict:
                                        amt_tot = internal_dict[o.product_id.id]
                                elif o.amount_select == 'fix':
                                    amt_tot = internal_dict[o.product_id.id]
#                                         amt_tot = amt_tot + (o.amount_fix * o.quantity)
                                              
                                percent1 = line.amount_percentage * line.quantity
                                amttotal = (amt_tot * percent1) / 100
                                sum_amt = amttotal
#                                 for tx_line in line.tax_id:
#                                     if tx_line.amount:
#                                         tx_tot = self.get_tax_total(tx_line, sum_amt)
                                if line.tax_id:
                                    tx_tot = self.get_tax_total(line.tax_id, sum_amt)
                                if tx_tot:
                                    line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                                    sum_amt = sum_amt + tx_tot
                                    line.write({'outstanding_product_amt':sum_amt})
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    internal_dict.update({line.product_id.id : sum_amt})
                                else:
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                                    internal_dict.update({line.product_id.id : sum_amt})
                                global_add3 = global_add3 + sum_amt
                                sum_amt = 0
                                
                elif line.amount_select == 'fix':
                    fix_amt = line.amount_fix * line.quantity
                    sum_amt = sum_amt + fix_amt
#                     for tx_line in line.tax_id:
#                         if tx_line.amount:
#                             tx_tot = self.get_tax_total(tx_line, sum_amt)
                    if line.tax_id:
                        tx_tot = self.get_tax_total(line.tax_id, sum_amt)
                    if tx_tot:
                        line.write({'product_amt':sum_amt,'outstanding_product_amt':sum_amt, 'tax_amount':tx_tot})
                        sum_amt = sum_amt + tx_tot
                        line.write({'outstanding_product_amt':sum_amt})
                        if line.product_id.id in internal_dict:
                            sum_amt = sum_amt + internal_dict[line.product_id.id]
                        internal_dict.update({line.product_id.id : sum_amt})
                    else:
                        if line.product_id.id in internal_dict:
                            sum_amt = sum_amt + internal_dict[line.product_id.id]
                        line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                        internal_dict.update({line.product_id.id : sum_amt})
                                  
                    global_add4 = global_add4 + sum_amt  
                    sum_amt = 0
                
                elif line.amount_select == 'code':
                    sum_amt = self.evaluate_python_code(line.amount_python_compute, approve_amt, interest_amt)
#                     for tx_line in line.tax_id:
#                         if tx_line.amount:
#                             tx_tot = self.get_tax_total(tx_line, sum_amt)
                    if line.tax_id:
                        tx_tot = self.get_tax_total(line.tax_id, sum_amt)
                    if tx_tot:
                        line.write({'product_amt':sum_amt,'outstanding_product_amt':sum_amt, 'tax_amount':tx_tot})
                        sum_amt = sum_amt + tx_tot
                        line.write({'outstanding_product_amt':sum_amt})
                        if line.product_id.id in internal_dict:
                            sum_amt = sum_amt + internal_dict[line.product_id.id]
                        internal_dict.update({line.product_id.id : sum_amt})
                    else:
                        if line.product_id.id in internal_dict:
                            sum_amt = sum_amt + internal_dict[line.product_id.id]
                        line.write({'product_amt':sum_amt,'outstanding_product_amt':sum_amt})
                        internal_dict.update({line.product_id.id : sum_amt})
                    sum_amt = 0
        
#         print (internal_dict,'sum of dictionalryeeeeeeeeeeeeeeeeeee')   
        if internal_dict:
            print ('to do list')
                
        total_all = sum(internal_dict.values())
        return total_all
    
    ##python code for execute expressions.............
    def evaluate_python_code(self, pycode=None, approve_amt=None, interest_amt=None):
        '''
            This function will calculate/evaluavate the python code in Loan Component Lines.
            @params :
            @returns : total
        '''
        try:
            if pycode and approve_amt and interest_amt:
                localdict = {'approve_amt': approve_amt, 'result':0.0, 'interest_amt':interest_amt}
                safe_eval(pycode, localdict, mode="exec", nocopy=True)
                return localdict['result'] or 0.0
            else:
                return 0.0
        except Exception as e:
            return 0.0
       
    @api.multi
    def _get_simple_int_by_existed_disbursed(self, inter_rate, disbursed_amt = 0.0, disburse_date=False, currency_id = False):
#         today_date = date.today()
#         disburse_date = (datetime.datetime.strptime(disburse_date, '%Y-%m-%d').date())
        disburse_date = disburse_date
        today_date = disburse_date
        count = 0
        installment_day = False
        sum_of_paid = 0.0
        counter_list = []
        main_prin_total = 0.0
        max_date = []
        if not self.repayment_basis == 'sanctioned_amt':
            for line in self.installment_id:
                # d = (datetime.datetime.strptime(line.date, '%Y-%m-%d')).date()
                d = line.date
                if line.state in ['paid','open']:
                    count = count + 1
                    if line.is_paid_installment == False:
                        counter_list.append(line)
                    max_date.append(line.date)
                else:
                    if line.state not in ['open','paid']:
                        if line.loan_id.cheque_ids:
                            line.loan_id.cheque_ids.unlink()
                        line.unlink()
                        
            if max_date:
                final_date = max(max_date)
#                 final_date = datetime.datetime.strptime(final_date, "%Y-%m-%d").strftime('%m/%d/%Y') 
                if final_date and disburse_date < final_date:
                    raise UserError(_('Please specify Disbursed Date greater than %s' % final_date))
                                   
            for l in counter_list:
                main_prin_total = main_prin_total + l.capital
                sum_of_paid = sum_of_paid + l.outstanding_prin
                if l.state == 'open':
                    l.capital = l.capital - l.outstanding_prin
                    l.outstanding_prin = 0.0
                    
                l.write({'is_paid_installment':True})
                # date_of_lines = (datetime.datetime.strptime(l.date, '%Y-%m-%d').date())
                date_of_lines = l.date
                installment_day = date_of_lines.day
                
        sum_of_paid = main_prin_total - sum_of_paid
        differ = self.old_disburse_amt - sum_of_paid  
        new_disburse = differ + disbursed_amt
        if  self._context.get('is_extended'):
            new_disburse = differ
            disbursed_amt = 0
        total_installment =  self.total_installment - count
        self.write({'old_disburse_amt':new_disburse})
        if installment_day:
            disburse_date = disburse_date.replace(day = installment_day)
            
        move_id = self._partial_by_disbursed(inter_rate, new_disburse, total_installment, disbursed_amt, disburse_date, currency_id)
        return move_id
    
    def check_date(self,date_update,new_day,present_month):
        if int(present_month) == 2:
            if int(date_update.year)%4 == 0:
                date_update = date_update.replace(day = 29,month = present_month)
            else:
                date_update = date_update.replace(day = 28,month = present_month)
        elif int(present_month) in [4,6,9,11] and new_day > 30:
            date_update = date_update.replace(day = 30,month = present_month)
        else:
            date_update = date_update.replace(day = new_day,month = present_month)
        return date_update
        
    def calculate_for_flat(self,num, date_update, disbursed_amt, total_installment, part_id):
#         print("\n\n\n Date UPdate ::: ",date_update)
        capital = round(disbursed_amt / float(total_installment),2)
        interest = round(((disbursed_amt / 100 * self.interest_rate)*(float(total_installment)/12.0))/float(total_installment),2)
        vals = {'name':'installment'+str(num), 'date':date_update,
                'loan_id':self.id, 'capital':capital, 
                'interest':interest, 'total':capital+interest, 
                'partner_id':part_id,'outstanding_prin':capital,'outstanding_int':interest,}
        return vals
    
    def calculate_for_constant_prin(self,num, date_update, disbursed_amt, total_amt, total_installment, part_id):
#         print("\n\n\n Date UPdate ::: ",date_update)

        capital = round(disbursed_amt / float(total_installment),2)
        interest = round(total_amt * self.interest_rate / 100)
        
        vals = {'name':'installment'+str(num), 'date':date_update, 
                'loan_id':self.id, 'capital':capital, 
                'interest':interest, 'total':capital+interest, 
                'partner_id':part_id,'outstanding_prin':capital,'outstanding_int':interest,}
        return vals
        
    ## partial disbursed amount      
    @api.multi
    def _partial_by_disbursed(self, inter_rate, disbursed_amt = 0.0,  total_installment = 0, actual_disbursed_amt = 0.0, disburse_date=False, currency_id = False):
        if not self.repayment_basis == 'sanctioned_amt':
            if not self.journal_disburse_id:
                raise UserError(_('Please Configure Loan Disbursement Journal'))
            loan = self.read()
            installment_cr = self.env['account.loan.installment']
            cheque_cr = self.env['account.loan.bank.cheque']
            if not self.partner_id:
                raise exceptions.except_orm(_('Field Required'), _('Please select Customer.'))
            
            part_id = self.partner_id.id
            int_rate = 0.0
            if self.return_type == 'cheque':
                bank_ids = self.bank_id
            
            inter_sed = self.loan_type
            if inter_sed:
                inter_cal_type = inter_sed.calculation
                if inter_cal_type:
                    if inter_cal_type == 'flat': 
                        if self.loan_amt > 0.0 and self.total_installment > 0:
                            pass
    #                         int_rate = self.calculate_eir(inter_rate, self.loan_amount, self.total_installment/ 12 , inter_rate, 0) 
                    elif inter_cal_type == 'reducing':       
                        int_rate = inter_rate
                        
            rate_interest = int_rate / 100
            total = disbursed_amt
            install_list = []
            check_list = []
            try:
                installment = round(((total * (rate_interest / 12)) / (1 - ((1 + rate_interest / 12) ** -(total_installment)))))
            except ZeroDivisionError:
                installment = 0
            
            i = 1
            j = 1
            interest = 0
            acc_loan_bank_cheque_obj = []
#             date_update = datetime.datetime.strptime(disburse_date, "%Y-%m-%d").date()
            date_update = disburse_date
            date_new = date.today()
            new_day = int(date_update.day)
#             if date_update != date_new:
#                 new_month = date_new.month
#                 new_year = date_new.year
#                 date_update = date_update.replace(month = new_month)
#                 date_update = date_update.replace(year = new_year)
            present_month = date_update.month
            cnt = 0
            remain_amount = 0.0
            numbering = 1
            if self._context.get('is_extended'):
                to_be_deleted = installment_cr.search([('state', '=', 'draft'), ('loan_id', '=', self.id)])
                to_be_deleted.unlink()
                # disbursed_amt = self.loan_amount
                # for line in self.installment_id:
                #     disbursed_amt -= line.capital
            for num in self.installment_id:
                numbering += 1
            remain_amount = 0.0
            for i in range(numbering,self.total_installment+1):
                installment_vals ={}
                if self.loan_type.calculation == 'reducing':
                    interest_month = round(((total * rate_interest) / 12), 2)
                    principle_amount = round(installment - interest_month, 2)
                    remain_amount = round(total - principle_amount, 2)
                    present_month += 1
                    if present_month > 12:
                        present_month = 1;
                        s = date_update.year + 1
                        date_update = date_update.replace(year = s);
                    if new_day > 28:
                            date_update = self.check_date(date_update,new_day,present_month)
                    date_update = date_update.replace(month = present_month);
                    
                    installment_vals = {'name':'installment' + str(i), 'date':date_update,\
                                        'loan_id':self.id, 'capital':principle_amount,\
                                        'interest':interest_month, 'total':principle_amount + interest_month , 'partner_id':part_id,\
                                        'outstanding_prin':principle_amount,'outstanding_int':interest_month,}
                elif self.loan_type.calculation == 'flat':
                    present_month += 1
                    if present_month > 12:
                        present_month = 1;
                        s = date_update.year + 1
                        date_update = date_update.replace(year = s);
                    if new_day > 28:
                            date_update = self.check_date(date_update,new_day,present_month)
                    date_update = date_update.replace(month = present_month);
                    
                    installment_vals = self.calculate_for_flat(i, date_update, disbursed_amt, total_installment, part_id)
                    interest_month = installment_vals['interest']
                else:
                    present_month += 1
                    if present_month > 12:
                        present_month = 1;
                        s = date_update.year + 1
                        date_update = date_update.replace(year = s);
                    if new_day > 28:
                            date_update = self.check_date(date_update,new_day,present_month)
                    date_update = date_update.replace(month = present_month);
                    
                    installment_vals = self.calculate_for_constant_prin(i, date_update, disbursed_amt, total, total_installment, part_id)
                    remain_amount = round(total - installment_vals['capital'], 2)
                    interest_month = installment_vals['interest']
                    
                    
                install_id = installment_cr.create(installment_vals)               
                install_list.append(install_id)
                total = remain_amount
                interest += interest_month
    #         self.write({'interest':interest,'old_disburse_amt':disbursed_amt,});
            if total and self.installment_id :
                self.get_rounding_amt(total, self.installment_id[-1])
            fees_vals = {}
            fees_amt = self._get_fees_amount(self.loan_type, disbursed_amt, interest)
            if fees_amt:
                for fees_line in self.loan_type.loan_component_ids:
                    if fees_line.type == 'fees' and fees_line.tenure == 'tenure':
                        fees_vals = self.get_fees_as_tenure(self.loan_type, fees_amt, total_installment)
                    elif fees_line.type == 'fees' and fees_line.tenure == 'month':
                        fees_vals.update({'fees_amt':fees_amt})
                    elif fees_line.type == 'fees' and fees_line.tenure == 'per_year':
                        fees_vals = self.get_fees_as_tenure(self.loan_type, fees_amt, total_installment)
            else:
                fees_vals.update({'fees_amt':0.0})
            
            for line in install_list:
                total_amt = 0.0
                vals_fee = {}
                total_amt = round(fees_vals['fees_amt'] + line.total, 2)
                if 'fees_amt' in fees_vals:
                    line.write({'fees':fees_vals['fees_amt'],'total':total_amt, 'outstanding_fees':fees_vals['fees_amt']})
                for fees_line in  line.loan_id.loan_type.loan_component_ids:
                    if fees_line.type == 'fees' and fees_line.tenure == 'tenure':
                        vals_fee.update({'installment_id':line.id,
                                                            'product_id':fees_line.product_id.id,
                                                            'name':fees_line.type,
                                                            })
                        
                        if 'actual_fee' in fees_vals:
                            vals_fee.update({'base':fees_vals['actual_fee']})
                            
                        if fees_line.tax_id and 'tax_amt' in fees_vals:
                            if 'base' in vals_fee:
                                vals_fee.update({'base':fees_vals['actual_fee'] + fees_vals['tax_amt']})
                        
                        if vals_fee:
                            self.env['fees.lines'].create(vals_fee)
                    elif fees_line.type == 'fees' and fees_line.tenure == 'month':
                        vals_fee.update({'installment_id':line.id,
                                                            'product_id':fees_line.product_id.id,
                                                            'name':fees_line.type,
                                                            'base':fees_line.product_amt+fees_line.tax_amount,})
                        
#                         if fees_line.tax_id:
#                             vals_fee.update({'tax':fees_line.tax_amount})
                        if vals_fee:
                            self.env['fees.lines'].create(vals_fee)
            if self.payment_freq == 'daily':
                self._get_daily_calculation()
            elif self.payment_freq == 'weekly':
                self._get_weekly_calculation()
            elif self.payment_freq == 'bi_month':
                self._get_bymonth_calculation()
            elif self.payment_freq == 'quarterly':
                self._get_calculation_quarterly()
            elif self.payment_freq == 'monthly':
                self._get_calculation_monthly()
            elif self.payment_freq == 'half_yearly':
                self._get_half_yearly()
            else:
                self._get_yearly()
        move_id = self.create_moves(actual_disbursed_amt, disburse_date, flag = False, currency_id=currency_id)
        return move_id
    
    
    def get_intstallments(self, total, rate_interest, total_installment):
        try:
            installment = round(((total * (rate_interest / 12)) / (1 - ((1 + rate_interest / 12) ** -(total_installment)))))
        except ZeroDivisionError:
            installment = 0
        return installment
    
    
#     def get_fees_as_tenure(self, loan_type, fee_amt, tot_installemnt):
#         ##code are here .....................
#         tx_tot = 0.0
#         fees_dict = {}
#         for line in loan_type.loan_component_ids:
#             if line.type == 'fees' and line.tenure == 'tenure':
#                 amt = round(fee_amt / tot_installemnt, 2)
#                 amt_fees = amt
#                 if line.tax_id and amt:
#                     tx_tot = self.get_tax_total_incl_exl(line.tax_id, amt)
#                 if tx_tot:
# #                     line.tax_amount = round(tx_tot, 2)
#                     amt_fees = amt_fees - tx_tot
#                 fees_dict.update({'fees_amt':amt, 'actual_fee':amt_fees,'tax_amt':tx_tot})
#             elif line.type == 'fees' and line.tenure == 'per_year':
#                 if tot_installemnt >= 1:
#                     main_amt = round((fee_amt/12)*tot_installemnt, 2)
#                     if main_amt:
#                         amt = main_amt / tot_installemnt 
#                     amt_fees = amt
#                 if line.tax_id and amt:
#                     tx_tot = self.get_tax_total_incl_exl(line.tax_id, amt)
#                 if tx_tot:
# #                     line.tax_amount = 
#                     amt_fees = amt_fees - tx_tot
#                 fees_dict.update({'fees_amt':amt, 'actual_fee':amt_fees,'tax_amt':tx_tot})
#         return fees_dict
    
    def get_fees_as_tenure(self, loan_type, fee_amt, tot_installemnt):
        ##code are here .....................
        tx_tot = 0.0
        fees_dict = {}
        for line in loan_type.loan_component_ids:
            if line.type == 'fees' and line.tenure == 'tenure':
                amt = round(fee_amt / tot_installemnt, 2)
                amt_fees = amt
                if line.tax_id and amt:
                    tx_tot = self.get_tax_total_incl_exl(line.tax_id, amt)
                if tx_tot:
#                     line.tax_amount = round(tx_tot, 2)
                    amt_fees = amt_fees - tx_tot
                fees_dict.update({'fees_amt':amt, 'actual_fee':amt,'tax_amt':tx_tot})
            elif line.type == 'fees' and line.tenure == 'per_year':
                if tot_installemnt >= 1:
                    main_amt = round((fee_amt/12)*tot_installemnt, 2)
                    if main_amt:
                        amt = main_amt / tot_installemnt 
                    amt_fees = amt
                if line.tax_id and amt:
                    tx_tot = self.get_tax_total_incl_exl(line.tax_id, amt)
                if tx_tot:
#                     line.tax_amount = 
                    amt_fees = amt_fees - tx_tot
                fees_dict.update({'fees_amt':amt, 'actual_fee':amt,'tax_amt':tx_tot})
        return fees_dict
    
    def get_grace_amount(self, tot_grc_amt, total_installment):
        amt = 0.0
        if tot_grc_amt and total_installment:
            amt = round(tot_grc_amt / total_installment,2)
        return amt
    
    
    def get_rounding_amt(self, total, installment):
        if installment.capital:
            installment.capital = installment.capital +  total
            installment.outstanding_prin = installment.outstanding_prin + total
            installment.total = installment.total + total
            
       
    @api.multi
    def _simple_interest_get_by_disbursed(self, inter_rate, disbursed_amt = 0.0, disburse_date=False, currency_id = False):
        loan = self.read()
        installment_cr = self.env['account.loan.installment']
        cheque_cr = self.env['account.loan.bank.cheque']
        move_obj = self.env['account.move']
        line_obj = self.env['account.move.line']
        
        if not self.partner_id:
            raise exceptions.except_orm(_('Field Required'), _('Please select Customer.'))
        
        part_id = self.partner_id.id
        int_rate = 0.0
        if self.return_type == 'cheque':
            bank_ids = self.bank_id
        
        inter_sed = self.loan_type
        if inter_sed:
            inter_cal_type = inter_sed.calculation
            if inter_cal_type:
                if inter_cal_type == 'flat': 
                    if self.loan_amount > 0.0 and self.total_installment > 0:
#                         int_rate = self.calculate_eir(inter_rate, self.loan_amount, self.total_installment / 12 , inter_rate, 0)
                        pass 
                elif inter_cal_type == 'reducing':       
                    int_rate = inter_rate
                    
        rate_interest = int_rate / 100
        updated_loan_amount = self.loan_amount
        if self.repayment_basis == 'sanctioned_amt':
            if self._context.get('is_extended'):
                to_be_deleted = installment_cr.search([('state', '=', 'draft'), ('loan_id', '=', self.id)])
                to_be_deleted.unlink()
                new_loan_amount = self.loan_amount
                for line in self.installment_id:
                    new_loan_amount -= line.capital
                # if self.loan_type.calculation == 'flat':
                updated_loan_amount = new_loan_amount
                total = new_loan_amount
                pr_total = new_loan_amount
                main_tot = new_loan_amount
            else:
                total = self.loan_amount
                pr_total = self.loan_amount
                main_tot = self.loan_amount
        else:
            total = disbursed_amt
            pr_total = disbursed_amt
            main_tot = disbursed_amt
            
            
        ##changes according to grace period of component lines.=========================================== 
        gp_int = 0
        gp_principal = 0
        gp_fee = 0 
        lst_gp = [] 
        global_dict = {} 
        key_min = None
        flag = True
        el_flag = True
        grc_installment = 0.0
        
        total_installment = self.total_installment
        for loan_com_line in self.loan_type.loan_component_ids:
            if loan_com_line.type == 'principal':
                gp_principal = loan_com_line.grace_period
                global_dict.update({'principal':gp_principal})
                lst_gp.append(loan_com_line.grace_period)
            if loan_com_line.type == 'int_rate':
                gp_int = loan_com_line.grace_period
                global_dict.update({'int_rate':gp_int})
                lst_gp.append(loan_com_line.grace_period)
            if loan_com_line.type == 'fees':
                gp_fee = loan_com_line.grace_period
                global_dict.update({'fees':gp_fee})
                lst_gp.append(loan_com_line.grace_period)
                
                
        if lst_gp and gp_fee == gp_int == gp_principal:
            total_installment = self.total_installment - (min(lst_gp))
            grc_installment = self.total_installment - total_installment
        ##================================================================================================
        total_installment = self.total_installment - len(self.installment_id)  - (min(lst_gp))
        grc_install = self.total_installment - total_installment
        if gp_fee == gp_int == gp_principal:  
            try:
                installment = round(((total * (rate_interest / 12)) / (1 - ((1 + rate_interest / 12) ** -(total_installment)))))
            except ZeroDivisionError:
                installment = 0
        else:
            try:
                installment = round(((total * (rate_interest / 12)) / (1 - ((1 + rate_interest / 12) ** -(self.total_installment)))))
            except ZeroDivisionError:
                installment = 0
        
        i = 1
        inst_num = len(self.installment_id)
        flat_int = 0
        tot_grc_int = 0.0
        tot_grc_capital = 0.0
        interest = 0
        sum_of_inst = 0.0
        cnt_fees_flag = False
        # date_update = datetime.datetime.strptime(disburse_date, "%Y-%m-%d").date()
        date_update = disburse_date
        new_day = int(date_update.day)
        
        if lst_gp:
            present_month = date_update.month + min(lst_gp)
            # print ("=========global_dict=======",global_dict)
            key_min = min(global_dict, key=lambda k: global_dict[k])
        else:
            present_month = date_update.month
            
        cnt = min(lst_gp)
        count_grace_line = 0
        numbering = 1
        for num in self.installment_id:
            numbering += 1
        remaining_instalment = self.total_installment + 1 - numbering
        for i in range(numbering, self.total_installment+1):
            grace_int = round(((main_tot * rate_interest) / 12), 2)
            principle_amount = 0.0
            interest_month = 0.0
            is_capital_pay = False
            int_for_prin = round(((total * rate_interest) / 12), 2)
            if not total_installment:
                raise Warning('Please Check grace periods in the loan component lines total installment and grace period should not be same')
            interest = round(((100000 / 100 * self.interest_rate)*(float(total_installment)/12.0))/float(total_installment),2)
            # print ("====gp_fee == gp_int == gp_principal=======",gp_fee,gp_int,gp_principal, key_min)
            if gp_fee == gp_int == gp_principal:
                if self.loan_type.calculation == 'flat':
                    if self.repayment_basis == 'sanctioned_amt':
                        capital = round(updated_loan_amount / float(remaining_instalment - global_dict.get('principal')),2)
                        interest = round(((updated_loan_amount / 100 * self.interest_rate)*(float(self.total_installment)/12.0))/float(self.total_installment),2)
                    else:
                        capital = round(disbursed_amt / float(self.total_installment - global_dict.get('principal')),2)
                        interest = round(((disbursed_amt / 100 * self.interest_rate)*(float(self.total_installment)/12.0))/float(self.total_installment),2)
                elif self.loan_type.calculation == 'reducing':
                    interest_month = round(((total * rate_interest) / 12), 2)
                    principle_amount = round(installment - interest_month, 2)
                else:
                    if self.repayment_basis == 'sanctioned_amt':
                        capital = round(updated_loan_amount / float(remaining_instalment - global_dict.get('principal')),2)
                        interest = round(total * self.interest_rate / 100)
                    else:
                        capital = round(disbursed_amt / float(self.total_installment - global_dict.get('principal')),2)
                        interest = round(total * self.interest_rate / 100)
                if i <= grc_installment:
                    principle_amount = 0.0
                    if self.loan_type.calculation == 'flat':
                        tot_grc_capital = tot_grc_capital + capital
                        tot_grc_int = tot_grc_int + interest
                    elif self.loan_type.calculation == 'reducing':
                        tot_grc_capital = tot_grc_capital + principle_amount
                        tot_grc_int = tot_grc_int + interest_month
                        remain_amount = round(total - principle_amount, 2)
                        total = remain_amount
                    else:
                        remain_amount = round(total - capital, 2)
                        total = remain_amount
                    continue
                inst_num = inst_num + 1
            else:
                cnt_fees_flag = True
                ## for interest calculations .............................
                if key_min == 'int_rate' :
                    if self.loan_type.calculation == 'flat':
                        if self.repayment_basis == 'sanctioned_amt':                
#                             capital = round(disbursed_amt / float(total_installment),2)
#                             print ("=============v===========",updated_loan_amount)
                            interest = round(((updated_loan_amount / 100 * self.interest_rate)*(float(total_installment)/12.0))/float(total_installment),2)
                            # print("\n\n\n\n INETREST 1111111111 :::: ",interest)
                        else:
                            interest = round(((disbursed_amt / 100 * self.interest_rate)*(float(total_installment)/12.0))/float(total_installment),2)
#                             print("\n\n\n\n INETREST 2222222222 :::: ",interest)
                    elif self.loan_type.calculation == 'reducing':
                        interest_month = round(((total * rate_interest) / 12), 2)
#                         print("\n\n\n\n INETREST 33333333333 :::: ",interest_month)
                    else:
                        interest = round(total * self.interest_rate / 100)
                    
                
                elif cnt >= global_dict.get('int_rate'):
                    if self.loan_type.calculation == 'flat':
                        if self.repayment_basis == 'sanctioned_amt':
#                             capital = round(disbursed_amt / float(total_installment),2)
                            interest = round(((updated_loan_amount / 100 * self.interest_rate)*(float(total_installment)/12.0))/float(total_installment),2)
                            # print("\n\n\n\n INETREST 4444444444 :::: ",interest)
                        else:
                            interest = round(((disbursed_amt / 100 * self.interest_rate)*(float(total_installment)/12.0))/float(total_installment),2)
#                             print("\n\n\n\n INETREST 555555555 :::: ",interest)
                    elif self.loan_type.calculation == 'reducing':
                        interest_month = round(((total * rate_interest) / 12), 2)
#                         print("\n\n\n\n INETREST 6666666666 :::: ",interest_month)
                    else:
                        interest = round(total * self.interest_rate / 100)
                else:
                    interest_month = 0.0
                    interest = 0.0
#                     temp_int = 0.0
#                     temp_int_mnth = 0.0
#                     if self.loan_type.calculation == 'flat':
#                         if self.repayment_basis == 'sanctioned_amt':
# #                             capital = round(disbursed_amt / float(total_installment),2)
#                             temp_int = round(((self.loan_amount / 100 * self.interest_rate)*(float(total_installment)/12.0))/float(total_installment),2)
#                         else:
#                             temp_int = round(((disbursed_amt / 100 * self.interest_rate)*(float(total_installment)/12.0))/float(total_installment),2)
#                     else:
#                         temp_int_mnth = round(((total * rate_interest) / 12), 2)
#                     if self.loan_type.calculation == 'flat':
#                         tot_grc_int = tot_grc_int + temp_int
#                     else:
#                         tot_grc_int = tot_grc_int + temp_int_mnth
                        
                ## for principal calculations .............................
                if key_min == 'principal':
                    if self.loan_type.calculation == 'flat':
                        if self.repayment_basis == 'sanctioned_amt':                
                            capital = round(updated_loan_amount / float(self.total_installment - global_dict.get('principal')),2)
                        else:
                            capital = round(disbursed_amt / float(self.total_installment - global_dict.get('principal')),2)
                    elif self.loan_type.calculation == 'reducing':
                        principle_amount = round(installment - int_for_prin, 2)
                    else:
                        if self.repayment_basis == 'sanctioned_amt':
                            capital = round(updated_loan_amount / float(self.total_installment - global_dict.get('principal')),2)
                        else:
                            capital = round(disbursed_amt / float(self.total_installment - global_dict.get('principal')),2)
                    
                elif cnt >= global_dict.get('principal'):
                    tot_inst = self.total_installment - i
                    if self.loan_type.calculation == 'flat':
                        if flag:
                            flag = False
                            if self.repayment_basis == 'sanctioned_amt':                
                                capital = round(updated_loan_amount / float(self.total_installment - global_dict.get('principal')),2)
                            else:
                                capital = round(disbursed_amt / float(self.total_installment - global_dict.get('principal')),2)
                    elif self.loan_type.calculation == 'reducing':
                        if flag:
                            flag = False
                            installment = self.get_intstallments(pr_total, rate_interest, tot_inst + 1)
                            int_month = round(((pr_total * rate_interest) / 12), 2)
                        principle_amount = round(installment - int_for_prin, 2)
                    else:
                        if self.repayment_basis == 'sanctioned_amt':                
                            capital = round(updated_loan_amount / float(self.total_installment - global_dict.get('principal')),2)
                        else:
                            capital = round(disbursed_amt / float(self.total_installment - global_dict.get('principal')),2)
                else:
                    principle_amount = 0.0
                    capital = 0.0
                    
#                     temp_capital = 0.0
#                     temp_cp_mnth = 0.0
#                     tot_inst = self.total_installment - i
#                     if self.loan_type.calculation == 'flat':
# #                         if el_flag:
# #                             el_flag = False
#                         if self.repayment_basis == 'sanctioned_amt':                
#                             temp_capital = round(self.loan_amount / float(self.total_installment),2)
#                         else:
#                             temp_capital = round(disbursed_amt / float(self.total_installment),2)
#                     else:
#                         if flag:
#                             flag = False
#                             installment = self.get_intstallments(pr_total, rate_interest, tot_inst + 1)
#                             temp_cp_mnth = round(((pr_total * rate_interest) / 12), 2)
#                         temp_cp_mnth = round(installment - int_for_prin, 2)
#                         
#                         
#                     if self.loan_type.calculation == 'flat':
#                         tot_grc_capital = tot_grc_capital + temp_capital
#                     else:
#                         tot_grc_capital = tot_grc_capital + temp_cp_mnth
#                     remain_amount = round(total - temp_cp_mnth, 2)
#                     total = remain_amount
                    
                if i <= grc_install:
                    if self.loan_type.calculation == 'flat':
                        tot_grc_capital = tot_grc_capital + capital
                        tot_grc_int = tot_grc_int + interest
                    elif self.loan_type.calculation == 'reducing':
                        tot_grc_capital = tot_grc_capital + principle_amount
                        tot_grc_int = tot_grc_int + interest_month
                        remain_amount = round(total - principle_amount, 2)
                        total = remain_amount
                    else:
                        remain_amount = round(total - capital, 2)
                        total = remain_amount
                        is_capital_pay = True
                    continue
                
                inst_num = inst_num + 1
                    
                        
            
            present_month += 1
            if present_month > 12:
                present_month = present_month - 12;
                s = date_update.year + 1
                date_update = date_update.replace(year = s);
            if new_day > 28:
                    date_update = self.check_date(date_update, new_day, present_month)
            date_update = date_update.replace(month = present_month);
            installment_vals = {}
            
            
            
            if self.loan_type.calculation == 'reducing':
                remain_amount = round(total - principle_amount, 2)
                sum_of_inst = sum_of_inst + principle_amount
                if principle_amount <= 0:
                    count_grace_line = 0
                    installment_vals = {'name':'installment' + str(inst_num),\
                                    'date':date_update, 'loan_id':self.id,\
                                    'capital':principle_amount, 'interest':grace_int,\
                                    'total':principle_amount + interest_month, 'partner_id':part_id,\
                                     'outstanding_prin':principle_amount,'outstanding_int':grace_int,\
                                     }
                else:
                    count_grace_line += 1
                    if count_grace_line == 1:
                        installment_vals = {'name':'installment' + str(inst_num),\
                                    'date':date_update, 'loan_id':self.id,\
                                    'capital':principle_amount, 'interest':grace_int,\
                                    'total':principle_amount + interest_month, 'partner_id':part_id,\
                                     'outstanding_prin':principle_amount,'outstanding_int':grace_int,\
                                     }
                    else:
                        installment_vals = {'name':'installment' + str(inst_num),\
                                    'date':date_update, 'loan_id':self.id,\
                                    'capital':principle_amount, 'interest':interest_month,\
                                    'total':principle_amount + interest_month, 'partner_id':part_id,\
                                     'outstanding_prin':principle_amount,'outstanding_int':interest_month,\
                                     }
            elif self.loan_type.calculation == 'flat':   
                remain_amount = round(total - capital, 2)     
                sum_of_inst = sum_of_inst + capital
                installment_vals = {'name':'installment'+str(inst_num), 'date':date_update, 
                        'loan_id':self.id, 'capital':capital, 
                        'interest':interest, 'total':capital+interest, 
                        'partner_id':part_id,'outstanding_prin':capital,'outstanding_int':interest,}
                interest_month = installment_vals['interest']
            else:
                if is_capital_pay == False:
                    if total:
                        remain_amount = round(total - capital, 2)     
                sum_of_inst = sum_of_inst + capital
                installment_vals = {'name':'installment'+str(inst_num), 'date':date_update, 
                        'loan_id':self.id, 'capital':capital, 
                        'interest':interest, 'total':capital+interest, 
                        'partner_id':part_id,'outstanding_prin':capital,'outstanding_int':interest,}
                interest_month = installment_vals['interest']
            installment_cr.create(installment_vals)
            total = remain_amount
            interest += interest_month
            cnt = cnt + 1
        self.write({'interest':interest,'old_disburse_amt':disbursed_amt,});

        ## Fee calculation .........................
        fees_vals = {}
        if self.repayment_basis == 'sanctioned_amt':
            fees_amt = self._get_fees_amount(self.loan_type, updated_loan_amount, interest)
            if fees_amt:
                for fees_line in self.loan_type.loan_component_ids:
                    if fees_line.type == 'fees' and fees_line.tenure == 'tenure':
                        fees_vals = self.get_fees_as_tenure(self.loan_type, fees_amt, self.total_installment - fees_line.grace_period)
                    elif fees_line.type == 'fees' and fees_line.tenure == 'month':
                        fees_vals.update({'fees_amt':fees_amt})
                    elif fees_line.type == 'fees' and fees_line.tenure == 'per_year':
                        fees_vals = self.get_fees_as_tenure(self.loan_type, fees_amt, self.total_installment-fees_line.grace_period)

#                     else:
#                         fees_vals.update({'fees_amt':fees_amt})
            else:
                fees_vals.update({'fees_amt':0.0})
        else:
            fees_amt = self._get_fees_amount(self.loan_type, disbursed_amt, interest)
            if fees_amt:
                for fees_line in self.loan_type.loan_component_ids:
                    if fees_line.type == 'fees' and fees_line.tenure == 'tenure':
                        fees_vals = self.get_fees_as_tenure(self.loan_type, fees_amt, self.total_installment - fees_line.grace_period)
                    elif fees_line.type == 'fees' and fees_line.tenure == 'month':
                        fees_vals.update({'fees_amt':fees_amt})
                    elif fees_line.type == 'fees' and fees_line.tenure == 'per_year':
                        fees_vals = self.get_fees_as_tenure(self.loan_type, fees_amt, self.total_installment-fees_line.grace_period)
#                     else:
#                         fees_vals.update({'fees_amt':fees_amt})
            else:
                fees_vals.update({'fees_amt':0.0})

        ##grace period principal and interest calculation ................
        grc_cp = 0.0
        grc_int = 0.0
        grc_fees = 0.0


        if total and self.installment_id:
            self.get_rounding_amt(total, self.installment_id[-1])

#         if tot_grc_capital and grc_installment:
#             grc_cp = self.get_grace_amount(tot_grc_capital, total_installment)
#
        if tot_grc_int and grc_installment:
            grc_int = self.get_grace_amount(tot_grc_int, total_installment)
#
#         if tot_grc_capital and cnt_fees_flag:
#             print (tot_grc_capital,'---------------------------cp1233')
#             if min(lst_gp) == 0 and gp_principal != 0:
#                 grc_cp = self.get_grace_amount(tot_grc_capital, self.total_installment - gp_principal)
#             else:
#                 if gp_principal != min(lst_gp):
#                     p = abs(gp_principal - min(lst_gp))
#                     grc_cp = self.get_grace_amount(tot_grc_capital, self.total_installment - p)

        if tot_grc_int and cnt_fees_flag:
#             print (tot_grc_int,'---------------------------in1233')
#             if min(lst_gp) == 0 and gp_int != 0:
            grc_int = self.get_grace_amount(tot_grc_int, self.total_installment - gp_int)
#             else:
#                 if gp_int != min(lst_gp):
#                     v = abs(gp_int - min(lst_gp))
#                     grc_int = self.get_grace_amount(tot_grc_int, self.total_installment - v)
        # for same grace period to all fees, capital, interest ...................
        if grc_installment:
            if 'fees_amt' in fees_vals and fees_vals['fees_amt']:
                grc_fees = fees_vals.get('fees_amt') * grc_installment
            if grc_fees:
                grc_fees = self.get_grace_amount(grc_fees, total_installment)
            #
        ## for random grace period to all fees, capital, interest ...................
        if cnt_fees_flag:
            if 'fees_amt' in fees_vals and fees_vals['fees_amt']:
                if min(lst_gp) == 0 and gp_fee != 0:
                    grc_fees = fees_vals.get('fees_amt') * gp_fee
                    if grc_fees:
                        grc_fees = self.get_grace_amount(grc_fees, self.total_installment - gp_fee)
#                 else:
#                     if gp_fee != min(lst_gp):
#                         a = abs(gp_fee - min(lst_gp))
#                         grc_fees = fees_vals.get('fees_amt') * a
#                         print (grc_fees,'========================')
#                         print (ddfdf)
#                     if grc_fees:
#                         grc_fees = self.get_grace_amount(grc_fees, self.total_installment - a)

#         print (grc_fees,grc_cp,grc_int,'----------------------------11111')
        if grc_cp  or grc_int:
            for ins_line in self.installment_id:
                if ins_line.capital:
                    ins_line.capital = (ins_line.capital +  grc_cp)
                    ins_line.total = ins_line.total + grc_cp
                if ins_line.interest:
                    ins_line.interest = (ins_line.interest +  grc_int)
                    ins_line.total = ins_line.total + grc_int
                if ins_line.outstanding_prin:
                    ins_line.outstanding_prin = (ins_line.outstanding_prin + grc_cp)
                if ins_line.outstanding_int:
                    ins_line.outstanding_int = (ins_line.outstanding_int +  grc_int)

        ## fee updating in installment line level ...................
        gp_fee_cnt = min(lst_gp)
        is_updated_fees = False
        for line in self.installment_id:
            if line.state in ['open', 'paid']:
                continue
            total_amt = 0.0
            vals = {}
            vals_fee = {}
            if gp_fee == gp_int == gp_principal:
                is_updated_fees = True
                if 'fees_amt' in fees_vals:
                    total_amt = fees_vals['fees_amt'] + line.total + grc_fees
                    line.write({'fees':fees_vals['fees_amt'] + grc_fees,'outstanding_fees':fees_vals['fees_amt'] + grc_fees, 'total':total_amt})
            else:
                if key_min == 'fees':
                    is_updated_fees = True
                    if 'fees_amt' in fees_vals:
                        total_amt = fees_vals['fees_amt'] + line.total + grc_fees
                        line.write({'fees':fees_vals['fees_amt'] + grc_fees,'outstanding_fees':fees_vals['fees_amt'] + grc_fees,'total':total_amt})
                elif gp_fee_cnt >= global_dict.get('fees'):
                    is_updated_fees = True
                    if 'fees_amt' in fees_vals:
                        total_amt = fees_vals['fees_amt'] + line.total + grc_fees
                        line.write({'fees':fees_vals['fees_amt'] + grc_fees,'outstanding_fees':fees_vals['fees_amt'] + grc_fees,'total':total_amt})
            if is_updated_fees:
                for fees_line in  line.loan_id.loan_type.loan_component_ids:
                    if fees_line.type == 'fees' and fees_line.tenure == 'month':
                        vals_fee.update({'installment_id':line.id,
                                                            'product_id':fees_line.product_id.id,
                                                            'name':fees_line.type,
                                                            'base':(fees_line.product_amt + fees_line.tax_amount + grc_fees),})
#                         if fees_line.tax_id:
#                             vals_fee.update({'tax':fees_line.tax_amount})
                        if vals_fee:
                            self.env['fees.lines'].create(vals_fee)
                    elif fees_line.type == 'fees' and fees_line.tenure == 'tenure':
                        vals_fee.update({'installment_id':line.id,
                                                        'product_id':fees_line.product_id.id,
                                                        'name':fees_line.type,
                                                        })

                        if 'actual_fee' in fees_vals:
                            vals_fee.update({'base':(fees_vals['actual_fee'] + grc_fees)})
#                         if fees_line.tax_id and 'tax_amt' in fees_vals:
#                             vals_fee.update({'tax':fees_vals['tax_amt']})
                        if vals_fee:
                            self.env['fees.lines'].create(vals_fee)

                    elif fees_line.type == 'fees' and fees_line.tenure == 'per_year':
                        vals_fee.update({'installment_id':line.id,
                                                        'product_id':fees_line.product_id.id,
                                                        'name':fees_line.type,
                                                        })

                        if 'actual_fee' in fees_vals:
                            vals_fee.update({'base':(fees_vals['actual_fee'] + grc_fees)})
#                         if fees_line.tax_id and 'tax_amt' in fees_vals:
#                             vals_fee.update({'tax':fees_vals['tax_amt']})
                        if vals_fee:
                            self.env['fees.lines'].create(vals_fee)

            gp_fee_cnt = gp_fee_cnt + 1
        ## line installment using by Payment Frequency.........................
        if self.payment_freq == 'daily':
            self._get_daily_calculation()
        elif self.payment_freq == 'weekly':
            self._get_weekly_calculation()
        elif self.payment_freq == 'bi_month':
            self._get_bymonth_calculation()
        elif self.payment_freq == 'quarterly':
            self._get_calculation_quarterly()
        elif self.payment_freq == 'monthly':
            self._get_calculation_monthly()
        elif self.payment_freq == 'half_yearly':
            self._get_half_yearly()
        else:
            self._get_yearly()
            
        move_id = self.create_moves(disbursed_amt, disburse_date, flag = True, currency_id= currency_id)
        return move_id
    
    ## yearly calcultion ..................
    def _get_yearly(self):
        cnt = 0
        inst = 'installment'
        cnt1 = 1
        cheque = 'cheque'
        principal = 0.0
        interest = 0.0
        fees = 0.0
        installment_ids = []
        vals = {}
        inst_list = []
        if (len(self.installment_id) % 12) != 0:
            raise UserError(_('You can not apply for yearly basis loan. Please check no. of installments.'))
        if self.payment_schedule_ids:
            self.payment_schedule_ids.unlink()
            
        for line in self.installment_id:
            principal = round(principal + line.capital,2)
            interest = round(interest + line.interest,2)
            fees = round(fees + line.fees,2)
            installment_ids.append(line)
            inst_list.append(line.id)
            if cnt == 11:
                date_update = line.date  
                total =  round(principal + interest + fees,2)
                vals.update({'name':inst+ str(cnt1), 'capital':principal,\
                             'interest':interest,'fees':fees,'total':total,\
                            'date':date_update, 'installment_id':[(6,0,inst_list)],'loan_id':self.id})
                inst_list = []
                if self.return_type == 'cheque':
                    vals1 = {'name':'cheque' + str(cnt1),\
                     'date':date_update, 'loan_id':self.id,\
                     'code':'cheque' + str(cnt1),'partner_id':line.partner_id.id,\
                     'cheque_amount':total, 'loan':principal, 'interest':interest,\
                     'account_id':self.journal_repayment_id.default_debit_account_id.id,\
                     'installment_id':line.id,'fees':fees}
                    cheque_id = self.env['account.loan.bank.cheque'].create(vals1)
                    vals.update({'cheque_id':cheque_id.id})
                    line.write({'cheque_id':cheque_id.id})
                    for l in installment_ids:
                        l.write({'cheque_id':cheque_id.id})
                    installment_ids = []
#                 vals.update({'loan_id':self.id})
                self.env['payment.schedule.line'].create(vals)
                vals = {}
                vals1 = {}
                principal = 0.0
                interest = 0.0
                fees = 0.0
                cnt1 = cnt1 + 1
                cnt = 0
            else:
                cnt = cnt + 1
    
    ## half yearly calculation ...........................
    def _get_half_yearly(self):
        cnt = 0
        inst = 'installment'
        cnt1 = 1
        cheque = 'cheque'
        principal = 0.0
        interest = 0.0
        fees = 0.0
        installment_ids = []
        vals = {}
        inst_list = []
        if self.payment_schedule_ids:
            self.payment_schedule_ids.unlink()
        if (len(self.installment_id) % 6) != 0:
            raise UserError(_('You can not apply for half yearly loan. Please check no. of installments.'))
            
        for line in self.installment_id:
            principal = principal + line.capital
            interest = interest + line.interest
            fees = fees + line.fees
            installment_ids.append(line)
            inst_list.append(line.id)
            if cnt == 5:
                date_update = line.date  
                total =  principal + interest + fees
                vals.update({'name':inst+ str(cnt1), 'capital':principal,\
                             'interest':interest,'fees':fees,'total':total,\
                            'date':date_update, 'installment_id':[(6,0,inst_list)]})
                inst_list = []
                if self.return_type == 'cheque':
                    vals1 = {'name':'cheque' + str(cnt1),\
                     'date':date_update, 'loan_id':self.id,\
                     'code':'cheque' + str(cnt1),'partner_id':line.partner_id.id,\
                     'cheque_amount':total, 'loan':principal, 'interest':interest,\
                     'account_id':self.journal_repayment_id.default_debit_account_id.id,\
                     'installment_id':line.id, 'fees':fees}
                    cheque_id = self.env['account.loan.bank.cheque'].create(vals1)
                    vals.update({'cheque_id':cheque_id.id})
                    line.write({'cheque_id':cheque_id.id})
                    for l in installment_ids:
                        l.write({'cheque_id':cheque_id.id})
                    installment_ids = []
                vals.update({'loan_id':self.id})
                self.env['payment.schedule.line'].create(vals)
                vals = {}
                vals1 = {}
                principal = 0.0
                interest = 0.0
                fees = 0.0
                cnt1 = cnt1 + 1
                cnt = 0
            else:
                cnt = cnt + 1
    
    
    ##monthly calculation .........................
    def _get_calculation_monthly(self):
        cnt1 = 1
        vals = {}
        cheque_cr = self.env['account.loan.bank.cheque']
        if self.payment_schedule_ids:
            self.payment_schedule_ids.unlink()
        for line in self.installment_id:
            
            vals = {'name':line.name, 'capital':line.capital,\
                             'interest':line.interest,'fees':line.fees,'total':line.total,\
                            'date':line.date, 'installment_id':[(6,0,[line.id])],'loan_id':self.id}
            if self.return_type == 'cheque': 
                cheque_id = cheque_cr.create({'name':'cheque' + str(cnt1), 'date':line.date,\
                                        'loan_id':line.loan_id.id, 'code':'cheque' + str(cnt1),\
                                        'partner_id':line.partner_id.id,\
                                        'cheque_amount':line.total, 'loan':line.capital, 'interest':line.interest,\
                                        'account_id':self.journal_repayment_id.default_debit_account_id.id,\
                                        'installment_id':line.id,'fees':line.fees})
                if cheque_id:
                    vals.update({'cheque_id':cheque_id.id})
                    line.write({'cheque_id':cheque_id.id})
#                     vals.update({'name':line.name, 'capital':line.capital,\
#                                      'interest':line.interest,'fees':line.fees,'total':line.total,\
#                                     'date':line.date, 'installment_id':line.id,'loan_id':self.id})
                    
            pyt_id = self.env['payment.schedule.line'].create(vals)
            cnt1 = cnt1 + 1
    ## Daily basis calculation ...................
    def _get_daily_calculation(self):
        inst = 'installment'
        principal = 0.0
        interest = 0.0
        fees = 0.0
        vals = {}
        cnt = 0
#         if self.payment_schedule_ids:
#             self.payment_schedule_ids.unlink()
        for line in self.installment_id:
            vals = {}
            inst_list = []
            total = 0.0
            if line.date:
                back_date = line.date - relativedelta(months=1)
                tot_days = (line.date - back_date).days
                principal = line.capital / tot_days
                interest = line.interest / tot_days
                fees = line.fees / tot_days
                total =  principal + interest + fees
                inst_list.append(line.id)
#                 if day_count == 0:
                    
                back_date = back_date + relativedelta(days=1)
                    
#                     day_count += 1
                for dline in range(tot_days):
                    cnt = cnt + 1
                    vals.update({'name':inst+ str(cnt), 'capital':principal,\
                             'interest':interest,'fees':fees,'total':total,\
                            'date':back_date, 'loan_id':self.id,'installment_id':[(6,0,inst_list)]}) 
                    self.env['payment.schedule.line'].create(vals)
                    back_date = back_date + relativedelta(days=1)
                    
        return True
                    
                    
    ## Weekly basis calculation ...................
    def _get_weekly_calculation(self):
        
        self._get_daily_calculation()
        inst = 'installment'
        principal = 0.0
        interest = 0.0
        fees = 0.0
        vals = {}
        cnt = 0
        cnt1 = 0
        count = 0
        list_vals = []
        py_line_len = len(self.payment_schedule_ids)
        for py_schule_line in self.payment_schedule_ids:
            principal = principal + py_schule_line.capital
            interest = interest + py_schule_line.interest
            fees = fees + py_schule_line.fees
            total = (principal + interest + fees)
            inst_list = []
            count += 1
            if py_line_len == count and cnt != 6:
                inst_list.append(py_schule_line.installment_id.id)
                cnt1 += 1
                vals.update({'name':inst+ str(cnt1), 'capital':principal,\
                             'interest':interest,'fees':fees,'total':total,\
                            'date':py_schule_line.date, 'loan_id':self.id,'installment_id':[(6,0,inst_list)]}) 
                list_vals.append(vals)
                
            if cnt == 6:
                inst_list.append(py_schule_line.installment_id.id)
                cnt1 += 1
                vals.update({'name':inst+ str(cnt1), 'capital':principal,\
                             'interest':interest,'fees':fees,'total':total,\
                            'date':py_schule_line.date, 'loan_id':self.id,'installment_id':[(6,0,inst_list)]}) 
#                 self.env['payment.schedule.line'].create(vals)
                list_vals.append(vals)
                principal = 0.0
                interest = 0.0
                fees = 0.0
                total = 0.0
                vals = {}
                cnt = 0
            else:
                cnt += 1
        if list_vals:
            self.payment_schedule_ids.unlink()
            for line in list_vals:
                self.env['payment.schedule.line'].create(line)
        return True
    
    
    ## by monthly basis calculation ...................
    def _get_bymonth_calculation(self):
        
        self._get_daily_calculation()
        inst = 'installment'
        principal = 0.0
        interest = 0.0
        fees = 0.0
        vals = {}
        cnt = 0
        cnt1 = 0
        count = 0
        list_vals = []
        py_line_len = len(self.payment_schedule_ids)
        for py_schule_line in self.payment_schedule_ids:
            principal = principal + py_schule_line.capital
            interest = interest + py_schule_line.interest
            fees = fees + py_schule_line.fees
            total = (principal + interest + fees)
            inst_list = []
            count += 1
            if py_line_len == count and cnt != 14:
                inst_list.append(py_schule_line.installment_id.id)
                cnt1 += 1
                vals.update({'name':inst+ str(cnt1), 'capital':principal,\
                             'interest':interest,'fees':fees,'total':total,\
                            'date':py_schule_line.date, 'loan_id':self.id,'installment_id':[(6,0,inst_list)]}) 
                list_vals.append(vals)
                
            if cnt == 14:
                inst_list.append(py_schule_line.installment_id.id)
                cnt1 += 1
                vals.update({'name':inst+ str(cnt1), 'capital':principal,\
                             'interest':interest,'fees':fees,'total':total,\
                            'date':py_schule_line.date, 'loan_id':self.id,'installment_id':[(6,0,inst_list)]}) 
#                 self.env['payment.schedule.line'].create(vals)
                list_vals.append(vals)
                principal = 0.0
                interest = 0.0
                fees = 0.0
                total = 0.0
                vals = {}
                cnt = 0
            else:
                cnt += 1
        if list_vals:
            self.payment_schedule_ids.unlink()
            for line in list_vals:
                self.env['payment.schedule.line'].create(line)
        return True
        
    
    ##Quarterly calculation .................
    def _get_calculation_quarterly(self):
        cnt = 0
        inst = 'installment'
        cnt1 = 1
        cheque = 'cheque'
        principal = 0.0
        interest = 0.0
        fees = 0.0
        vals = {}
        installment_ids = []
        inst_list = []
        if (len(self.installment_id) % 3) != 0:
            raise UserError(_('You can not apply for quarterly basis loan. Please check no. of installments.'))
        if self.payment_schedule_ids:
            self.payment_schedule_ids.unlink()
        for line in self.installment_id:
            principal = principal + line.capital
            interest = interest + line.interest
            fees = fees + line.fees
            installment_ids.append(line)
            inst_list.append(line.id)
            if cnt == 2:
                date_update = line.date  
                total =  principal + interest + fees
                vals.update({'name':inst+ str(cnt1), 'capital':principal,\
                             'interest':interest,'fees':fees,'total':total,\
                            'date':date_update, 'installment_id':[(6,0,inst_list)]})
                inst_list = []
                if self.return_type == 'cheque':
                    vals1 = {'name':'cheque' + str(cnt1),\
                     'date':date_update, 'loan_id':self.id,\
                     'code':'cheque' + str(cnt1),'partner_id':line.partner_id.id,\
                     'cheque_amount':total, 'loan':principal, 'interest':interest,\
                     'account_id':self.journal_repayment_id.default_debit_account_id.id,\
                     'installment_id':line.id,'fees':fees}
                    cheque_id = self.env['account.loan.bank.cheque'].create(vals1)
                    vals.update({'cheque_id':cheque_id.id})
                    line.write({'cheque_id':cheque_id.id})
                    for l in installment_ids:
                        l.write({'cheque_id':cheque_id.id})
                    installment_ids = []
                        
                vals.update({'loan_id':self.id})
                self.env['payment.schedule.line'].create(vals)
                vals = {}
                vals1 = {}
                principal = 0.0
                interest = 0.0
                fees = 0.0
                cnt1 = cnt1 + 1
                cnt = 0
            else:
                cnt = cnt + 1
                
    def create_moves(self, disburse_amt, disburse_date, flag, currency_id):
        ## accounting journal entries ..........................
        move_vals = {}
        name_des = "Loan Disbursement For: "
        name_processing_fees = "Processing Fee Collected For: "
        name_bank_deposite = "Amount Deposited In Customer Account For: "
        date_new = disburse_date
        move_lines_cr = {}
        move_lines_dr = {}
        processing_fee = {}
        list_mv_line = []
        gl_code = False
        move_id = False
        amount_currency = False
        fee_cnt = 0.0
        
        if not currency_id:
            raise UserError(_('Please Configure Currency'))
        
        if not self.company_id.currency_id:
            raise UserError(_('Please Configure Currency'))
        company_curren = self.company_id.currency_id
        
        if not self.journal_disburse_id:
                raise UserError(_('Please Configure Loan Disbursement Journal'))
        if self.loan_type:
            for type_line in self.loan_type.loan_component_ids:
                if type_line.type == 'principal':
                    if not type_line.gl_code:
                        raise UserError(_('Please Configure GLCode For Principal Amount'))
                    gl_code = type_line.gl_code.id
                    
        if self.loan_id:
            move_vals.update({'name':'/','ref':name_des + self.loan_id,\
                              'date':date_new,'journal_id':self.journal_disburse_id.id,\
                              })
            
            ##calculation for processing fee .............................
            if self.process_fee and flag:
                if not self.proc_fee:
                    raise UserError(_('Please Configure Processing Fee Journal'))
                
                if company_curren:
                    if currency_id.id != company_curren.id:
                        amount_currency = self.process_fee
                        amount = company_curren.with_context(date=date_new).compute(self.process_fee, currency_id)
                        fee_cnt = amount
                    else:
                        amount_currency = False
                if not amount_currency:
                    processing_fee.update({
                                            'account_id':self.proc_fee.id,
                                            'name':name_processing_fees+self.loan_id,
                                            'debit':0.0,
                                            'credit':self.process_fee,
                                            'partner_id':self.partner_id.id,
                        })
                else:
                    processing_fee.update({
                                            'account_id':self.proc_fee.id,
                                            'name':name_processing_fees+self.loan_id,
                                            'debit':0.0,
                                            'credit':amount,
                                            'partner_id':self.partner_id.id,
                                            'amount_currency':-amount_currency,
                                            'currency_id':currency_id.id
                        })
                    
                list_mv_line.append((0, 0, processing_fee))
                
            ## calculations for disburse debit amount ............................     
            if company_curren:
                if currency_id.id != company_curren.id:
                    amount_currency = disburse_amt
                    amount = company_curren.with_context(date=date_new).compute(disburse_amt, currency_id)
                else:
                    amount_currency = False
            if not amount_currency:
                move_lines_dr.update({
                                'account_id':gl_code,
                                'name':name_des+ self.loan_id,
                                'debit':disburse_amt,
                                'credit':0.0,
                                'partner_id':self.partner_id.id,
                                
                    })
            else:
                move_lines_dr.update({
                                'account_id':gl_code,
                                'name':name_des+ self.loan_id,
                                'debit':amount,
                                'credit':0.0,
                                'partner_id':self.partner_id.id,
                                'amount_currency':amount_currency,
                                'currency_id':currency_id.id
                                
                    })
            
            
            list_mv_line.append((0, 0, move_lines_dr))
            
            ## calculations for disburse credit amount ............................
            if company_curren:
                if currency_id.id != company_curren.id:
                    amount_currency = disburse_amt
                    amount = company_curren.with_context(date=date_new).compute(disburse_amt, currency_id)
                else:
                    amount_currency = False
                    
            if not amount_currency:
                move_lines_cr.update({
                                'account_id':self.journal_disburse_id.default_credit_account_id.id,
                                'name':name_bank_deposite+ self.loan_id,
                                'credit':disburse_amt,
                                'debit':0.0,
                                'partner_id':self.partner_id.id,
                    })
                if flag:
                    move_lines_cr['credit'] = disburse_amt - self.process_fee
            else:
                move_lines_cr.update({
                                'account_id':self.journal_disburse_id.default_credit_account_id.id,
                                'name':name_bank_deposite+ self.loan_id,
                                'credit':amount,
                                'debit':0.0,
                                'partner_id':self.partner_id.id,
                                'amount_currency':-amount_currency,
                                'currency_id':currency_id.id
                    })
                
                if flag:
                    move_lines_cr['credit'] = amount - fee_cnt
                    move_lines_cr['amount_currency'] = -amount_currency - (-self.process_fee)
            
            list_mv_line.append((0, 0, move_lines_cr))
            move_vals.update({'line_ids':list_mv_line})
            move_id = self.env['account.move'].create(move_vals)
            if move_id:
                move_id.post()
                return move_id
            
    
    @api.multi
    def _simple_interest_get(self, inter_rate):
        loan = self.read()
        installment_cr = self.env['account.loan.installment']
        cheque_cr = self.env['account.loan.bank.cheque']
        if not self.partner_id:
            raise exceptions.except_orm(_('Field Required'), _('Please select Customer.'))
        
        part_id = self.partner_id.id
        int_rate = 0.0
        if self.return_type == 'cheque':
            bank_ids = self.bank_id
        
        inter_sed = self.loan_type
        if inter_sed:
            inter_cal_type = inter_sed.calculation
            if inter_cal_type:
                if inter_cal_type == 'flat': 
                    if self.loan_amount > 0.0 and self.total_installment > 0:
                        int_rate = self.calculate_eir(inter_rate, self.loan_amount, self.total_installment / 12 , inter_rate, 0) 
                elif inter_cal_type == 'reducing':       
                    int_rate = inter_rate
                    
        rate_interest = int_rate / 100
        total = self.loan_amount
        approve_amt = self.approve_amount
        interest_amt = self.interest 
        fees_amt = self._get_fees_amount(self.loan_type, approve_amt, interest_amt)
        try:
            installment = round(((total * (rate_interest / 12)) / (1 - ((1 + rate_interest / 12) ** -(self.total_installment)))))
        except ZeroDivisionError:
            installment = 0
        
        i = 1
        j = 1
        interest = 0
        acc_loan_bank_cheque_obj = []
        date_update = datetime.date(2000, 0o1, 0o7)
        date_new = date.today()
        if date_update != date_new:
            new_month = date_new.month
            new_year = date_new.year
            date_update = date_update.replace(month = new_month)
            date_update = date_update.replace(year = new_year)
        present_month = date_update.month
        cnt = 0
        
        numbering = 1
        for num in self.installment_id:
            numbering += 1
        for i in range(numbering,self.total_installment+1):
            interest_month = round(((total * rate_interest) / 12))
            principle_amount = round(installment - interest_month)
            remain_amount = round(total - principle_amount)
            if self.return_type == 'cheque':
                present_month += 1
                if present_month > 12:
                    present_month = 1;
                    s = date_update.year + 1
                    date_update = date_update.replace(year = s);
                
                date_update = date_update.replace(month = present_month);
                j += 1; 
                vals = {'name':'cheque' + str(i),\
                 'date':date_update, 'loan_id':self.id,\
                 'code':'cheque' + str(i),'partner_id':part_id,\
                 'cheque_amount':installment, 'loan':principle_amount, 'interest':interest_month}
                if bank_ids:
                    vals.update({'loan_bank_id':bank_ids.id})
                ##remove customer bank account _id which is taken from res_partner_bank object  ....
                if self.bank_acc:
                    vals.update({'account_id':self.bank_acc.id})
#                 if acc_ids:
#                     vals.update({'account_id':acc_ids[0]})
                ##create loan lines ....................
                acc_loan_bank_cheque_obj = cheque_cr.create(vals)
            for item in acc_loan_bank_cheque_obj:
                installment_cr.create({'name':'installment' + str(i), 'loan_id':self.id, 'capital':principle_amount, 'fees':fees_amt,'interest':interest_month, 'total':installment, 'cheque_id':item.id, 'partner_id':part_id})            
                total = remain_amount
                interest += interest_month
#                 i += 1
        self.write({'interest':interest});
        for line in self.installment_id:
            total_amt = 0.0
            total_amt = line.fees + line.total
            line.write({'total':total_amt})
#         d_l = self.read(['apply_date'])[0]
        curr_date = self.apply_date
        sal_obj = self
        gross = self.loan_amount
        pr_fee = self.process_fee
        amt = self.approve_amount
        emp_name = self.partner_id.name
        journal_id = self.env['account.journal'].search([('name', '=', 'Bank')])[0]
        
        acc_move_line_name = emp_name
        try:
            move_vals = {
                       'acc_loan_id': self.id,
                       'name': acc_move_line_name,
                       'date': curr_date,
                       'account_id':sal_obj.proc_fee.id,
                       'credit': pr_fee ,
                       'debit':0.0,
                       'journal_id' : 5
                       }
            
            move_vals1 = {
                        'acc_loan_id': self.id,
                        'name': acc_move_line_name,
                        'date': curr_date,
                        'account_id':sal_obj.partner_id.property_account_payable_id.id,
                        'credit': amt ,
                        'debit':0.0,
                        'journal_id' : 5
                        }
        
            move_vals2 = {
                         'acc_loan_id': self.id,
                         'name': acc_move_line_name,
                         'date': curr_date,
                         'account_id': sal_obj.cus_pay_acc.id,
                         'debit': gross ,
                         'credit' : 0.0,
                         'journal_id' : 5
                         }   
            self.env['account.move'].create({'name': '/', 'partner_id': self.partner_id.id, 'journal_id': journal_id.id, 'date': curr_date, 'line_ids':[(0, 0, move_vals), (0, 0, move_vals1), (0, 0, move_vals2)]})
        except:
            raise UserError(_('Could not create account move lines.'))
            

    @api.multi
    def reject_loan(self):
        for loan in self:
            if loan.voucher_id and loan.voucher_id.state not in ('draft', 'cancel'):
                raise exceptions.except_orm(_('Could not Reject Loan !'), _('You must first cancel invoice attaced to this loan.'))
#                 raise osv.except_osv(
#                    'Could not Reject Loan !',
#                    'You must first cancel invoice attaced to this loan.')

        installment_cr = self.env['account.loan.installment']
        install_ids = installment_cr.search([('loan_id', '=', self.id)])
        for install_id in install_ids:
            install_id.unlink()
        cheque_cr = self.env['account.loan.bank.cheque']
        chq_ids = cheque_cr.search([('loan_id', '=', self.id)])
        for chq_id in chq_ids:
            chq_id.unlink()
        
        acc_move_line = self.env['account.move.line']
        ac_ids = acc_move_line.search([('acc_loan_id', '=', self.id)])
        for acc_id in ac_ids:
            acc_id.unlink()
        
        return True

    @api.multi
    def proof_approval(self):
        for loan in self:
            print("")
            if loan.loan_type:
                prooftype_req = loan.loan_type.prooftypes
                for pt in prooftype_req:
                    avail_proof_docs = self.env['account.loan.proof'].search([('loan_id', '=', loan.id), ('type', '=', pt.name), ('state', '=', 'done')])
                    if not avail_proof_docs:
                        raise exceptions.except_orm(_('Field Required'), _('This loan object has not valid ' + pt.name + ' proofs so please submit proof again and valid it.'))
#                         raise osv.except_osv('Field Required','This loan object has not valid ' + pt.name + ' proofs so please submit proof again and valid it')
                self.write({'state':'apply'})
            else:
                raise exceptions.except_orm(_('Information Required'), _('Loan Type is Not Defined.'))
#                 raise osv.except_osv('Information Required','Loan Type is Not Defined')

     
    @api.multi
    def apply_loan(self):
        for loan in self:
            if loan.loan_type.calculation == 'flat':
                interest_rate1 = self._simple_interest_get(loan.interest_rate)
            else:
                interest_rate1 = self._simple_interest_get(loan.interest_rate)
    
    @api.multi
    def button_cancel_loan(self):
        is_disburse = False
        is_payment = False
        for disburse_line in self.disbursement_details:
            if disburse_line.release_number and disburse_line.release_number.state != 'post':
                print ('for Disbursement entry cancel')
            if disburse_line.release_number:
                cancel_entry = disburse_line.release_number.button_cancel()
                if cancel_entry:
                    disburse_line.release_number.unlink()
                    disburse_line.unlink()
                    is_disburse = True
                    
        for repayment_line in self.repayment_details:
            if repayment_line.release_number and repayment_line.release_number != 'post':
                print ('For Payment Cancel')
            if repayment_line.release_number:
                py_cancel_entry = repayment_line.release_number.button_cancel()
                if py_cancel_entry:
                    repayment_line.release_number.unlink()
                    repayment_line.unlink()
                    is_payment = True
        self.state = 'cancel'
        return True
    
    ##manually added fees 
    def button_fees_calculation(self):
        ## Fee calculation .........................
        fees_vals = {}
        product_id = False
        late_fee_prodcut = False
        late_tax_id = False
        tax_id = False
        for type_details in self.loan_type.loan_component_ids:
            if type_details.type == 'fees':
                if type_details.product_id:
                    product_id = type_details.product_id.id
                if type_details.tax_id:
                    tax_id = type_details.tax_id
            if type_details.type == 'late_fee':
                if type_details.product_id:
                    late_fee_prodcut = type_details.product_id.id
                if type_details.tax_id:
                    late_tax_id = type_details.tax_id
        
        for line in self.installment_id:
            fees_vals = {}
            late_fees_vals = {}
            if line.state not in  ['open','paid'] and line.outstanding_fees:
                fees_line_id = self.env['fees.lines'].search([('product_id','=',product_id),('installment_id','=',line.id)], limit=1)
                fees_amt = line.outstanding_fees
                if tax_id: 
                    tx_tot = self.get_tax_total_incl_exl(tax_id, line.outstanding_fees)
                    fees_amt = fees_amt - tx_tot
                    fees_vals.update({'tax':tx_tot})
                fees_vals.update({'name':'fees','product_id':product_id, 'base':fees_amt,'installment_id':line.id})
                
                if not fees_line_id:
                    self.env['fees.lines'].create(fees_vals)
                
            if line.state not in  ['open','paid'] and line.late_fee:
                late_fees_amt = line.late_fee
                late_fees_line_id = self.env['fees.lines'].search([('product_id','=',late_fee_prodcut),('installment_id','=',line.id)], limit=1)
                if late_tax_id: 
                    tx_tot = self.get_tax_total_incl_exl(late_tax_id, line.late_fee)
                    late_fees_amt = late_fees_amt - tx_tot
                    late_fees_vals.update({'tax':tx_tot})
                late_fees_vals.update({'name':'late_fee', 'product_id':late_fee_prodcut, 'base':late_fees_amt,'installment_id':line.id})
                if not late_fees_line_id:
                    self.env['fees.lines'].create(late_fees_vals)
        return True
                
                    
    
    @api.multi
    def approve_loan(self):
        context = dict(self.env.context or {})
        context['active_id'] = self.id
        return {
            'name': _('Disbursement Wizard'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'loan.disbursement.wizard',
            'view_id': self.env.ref('pragtech_loan_advance.loan_disbursement_wizard_form_view').id,
            'type': 'ir.actions.act_window',
            'res_id': self.env.context.get('id'),
            'context': {'default_name':'Repayment Schedule Shall be Generated On "%s". Do you want to continue ?'%(dict(self._fields['repayment_basis'].selection).get(self.repayment_basis))},
            'target': 'new'
        }
        


    @api.multi
    def approve_proofs(self):
        if self.is_collateral and (not self.collateral_lines):
            raise UserError("Dear applicant please provide collateral details")
        if self.partner_id.is_group and (not self.group_members):
                raise UserError("Please provide name of group members before you proceed further.")
#         if not self.proof_id:
#             raise UserError("Dear applicant please provide proofs")
#         else:
#             if self.loan_type.prooftypes:
#                 required_proof_ids = []
#                 for type in self.loan_type.prooftypes:
#                     if type.is_mandatory:
#                         required_proof_ids.append(type.name.id)
#                 if len(self.proof_id) < len(required_proof_ids):
#                     proof_names = []
#                     st = ''
#                     for x in self.loan_type.prooftypes:
#                         if x.is_mandatory:
#                             proof_names.append(x.name.name)
#                     for p in proof_names:
#                         st = st +'\n'+str(p)
#                     raise UserError("Following proofs are mandatory: %s"%st)
#                 proof_type = []
#                 for proof in self.proof_id:
#                     if proof.type:
#                         proof_type.append(proof.type.name.id)
#                 for proof in required_proof_ids:
#                     if not proof in proof_type:
#                         proof_name = self.env['account.loan.proof.type'].search([('id','=',proof)])
#                         raise UserError("Following mandatory proof is still missing:\n %s"%proof_name.name)
#             if not self.cus_pay_acc or not self.bank_acc or not self.int_acc or not self.proc_fee:
#                 raise UserError("Please provide value for : \n\n- Customer Loan Account,\n- Interest Account,\n- Processing Fee Account, \n- Bank Account")
            
        self.write({'state':'apply'})
        
    @api.multi   
    def approve_finance(self):
        
        if not self.proof_id:
            raise UserError("Dear applicant please provide proofs")
        else:
            if self.loan_type.prooftypes:
                required_proof_ids = []
                for type in self.loan_type.prooftypes:
                    if type.is_mandatory:
                        required_proof_ids.append(type.name.id)
                if len(self.proof_id) < len(required_proof_ids):
                    proof_names = []
                    st = ''
                    for x in self.loan_type.prooftypes:
                        if x.is_mandatory:
                            proof_names.append(x.name.name)
                    for p in proof_names:
                        st = st +'\n'+str(p)
                    raise UserError("Following proofs are mandatory: %s"%st)
                proof_type = []
                for proof in self.proof_id:
                    if proof.type:
                        proof_type.append(proof.type.name.id)
                for proof in required_proof_ids:
                    if not proof in proof_type:
                        proof_name = self.env['account.loan.proof.type'].search([('id','=',proof)])
                        raise UserError("Following mandatory proof(s) is/are still missing:\n %s"%proof_name.name)
            
        if self.loan_amount <= 0:
            raise UserError("Sanctioned amount cannot be \"0.00\"")
        self.loan_interest_get()
        self.cal_amt()
        template = self.env.ref('pragtech_loan_advance.email_template_loan_sanction')
        mail_obj = self.env['mail.template'].browse(template.id).sudo()
        mail_obj.send_mail(self.id)
        if self.message_follower_ids and self.message_follower_ids[0].partner_id:
            for user in self.message_follower_ids:
                if not user.id == self.partner_id.id: 
                    mail_obj.partner_to = user.id
                    mail_obj.sudo().send_mail(self.id)
#         self.apply_loan()
        self.write({'state':'apply'})
        
        
    @api.multi    
    def loan_cancel(self):
        
        if self.voucher_id and self.voucher_id.state not in ('draft','cancel'):
            raise osv.except_osv(
                    'Could not Reject Loan !',
                    'You must first cancel Voucher attached to this loan.')
            
        self.installment_id.unlink()
        self.cheque_ids.unlink()
        acc_move_line = self.env['account.move.line']
        ac_ids =  acc_move_line.search([('acc_loan_id','=', self.id)]);
        ac_ids.unlink();
        self.write({'state':'cancel'})
        
        return True    
        
        
    @api.multi   
    def loan_cancel1(self):
        self.write({'state':'cancel'})
        
    
    @api.multi
    def loan_paid(self):
        for line in self.installment_id:
            if not line.state == 'paid':
                raise UserError("Warning : This loan application can not be marked as Done as there is some installment amount still pending.")
        voucher_dict = {
#             'draft':['open_voucher','proforma_voucher'],
            'draft':['proforma_voucher'],
            'proforma':['proforma_voucher']
        }
        voucher_pool = self.env['account.voucher']
        for this_obj in self:
            voucher_obj = this_obj.voucher_id and this_obj.voucher_id or False
            voucher_state = voucher_obj and voucher_obj.state or False
            if voucher_state and voucher_state in voucher_dict:
                for voucher_method in voucher_dict[voucher_state]:
#                     values = this_obj.voucher_id.id
                    getattr(voucher_pool, voucher_method)

            move_id = voucher_obj and [x.id for x in voucher_obj.move_id] or []
            if move_id:
                self.env['account.move.line'].write({'acc_loan_id':this_obj.id})
#                  self.pool.get('freight.vehicle').write(cr, uid, [self_brw.name.id], {'state': 'available'})
        self.date_done = date.today()
        
        self.write({'state':'done'})
        return True
    
    @api.multi
    def loan_draft(self):
        self.write({'state':'draft'})
        
        
    def loan_classification_status(self):
        records = self.search([])
#         print ('days calucation herer',self)
        date = datetime.datetime.now().date()
        for loan in records:
            arrear_day = 0
            for inst in loan.installment_id:
                if inst.date:
                    # if datetime.datetime.strptime(str(inst.date), "%Y-%m-%d") < date and inst.state != 'paid': #== 'draft'
                    if inst.date < date and inst.state != 'paid': #== 'draft'
                    # date = str(date).split()
                    # print("-------------------> ",inst.date,type(inst.date),date,type(date),date[0])

                    # if str(inst.date) < date[0] and inst.state != 'paid': #== 'draft'
                            if not arrear_day:
                                arrear_day = inst.date
            if arrear_day:
                    # arrear_day = datetime.datetime.strptime(arrear_day, "%Y-%m-%d")
                    arrear_day = arrear_day
                    print("arrear_day----------------------> ",date,type(date),type(arrear_day),arrear_day)
                    arrear_day =  date - arrear_day
                    arrear_day = arrear_day.days
            
            classification = None
            if arrear_day > 360:
                classification = self.env['loan.classifications'].search([('min','<=',arrear_day)])
            else:
                classification = self.env['loan.classifications'].search([('min','<=',arrear_day),('max','>=',arrear_day)])
                
            if classification:
                loan.write({'classification':classification[0].name})
                    
    def loan_due_cron(self):
        records = self.search([])
        for record in records:
            for line in record.installment_id:
                if line.date:
                    # if(datetime.datetime.strptime(line.date, "%Y-%m-%d").date() <= date.today()) and line.state != 'paid':
                    if(line.date <= date.today()) and line.state != 'paid':
#                         print(datetime.datetime.strptime(line.date, "%Y-%m-%d").date())
                        line.due_principal = line.outstanding_prin
                        line.due_interest = line.outstanding_int
                        line.due_fees = line.outstanding_fees
#                         total = line.outstanding_prin + line.outstanding_int + line.outstanding_fees
#                         line.installment_due = total
                        
    ##thisn for late fee calculation .................                  
    def loan_late_fees(self):
        records = self.search([('state', 'in', ['approved','partial'])])
        current_date = datetime.date.today()
#         current_date = datetime.date(2018,11,13)
        vals_fee = {}
#         records = self.env['account.loan'].browse(46)
        for record in records:
            if record.grace_period:
                for py_line in record.payment_schedule_ids:
                    is_grace_period = False
                    last_record = False
                    for line in py_line.installment_id:
                        
                        if line.state == 'draft':
                            is_grace_period = True
                            last_record = line
                        else:
                            is_grace_period = False
                            last_record = False
                            break
                    if is_grace_period and last_record:
    #                     date_object = (datetime.datetime.strptime(last_record.date, '%Y-%m-%d').date()+relativedelta(days = record.grace_period))
                        total = 0.0
                        # date_object = (datetime.datetime.strptime(last_record.date, '%Y-%m-%d').date())
                        date_object = last_record.date
                        delta = current_date - date_object
                        diff = int(delta.days / record.grace_period)
                        if diff > 0:
                            if record.repayment_basis == 'sanctioned_amt':
                                total = self._get_late_fees_amount(record.loan_type, record.loan_amount, record.interest)
                            else:
                                dis_amt = 0.0
                                for line in record.disbursement_details:
                                    dis_amt = dis_amt + line.disbursement_amt
                                    
                                if dis_amt > 0.0:   
                                    total = self._get_late_fees_amount(record.loan_type, dis_amt, record.interest)
                        
                        if total:
                            for cmp_line in record.loan_type.loan_component_ids:
                                
                                if cmp_line.type == 'late_fee':
                                    search_id = self.env['fees.lines'].search([('product_id','=', cmp_line.product_id.id),('installment_id','=', last_record.id)])
                                    if search_id:
                                        if cmp_line.product_amt:
                                            base_amt = (cmp_line.product_amt * diff)
                                            if cmp_line.tax_amount > 0.0 and cmp_line.tax_id:
                                                base_amt = base_amt + (cmp_line.tax_amount * diff)
                                            search_id.write({'base':base_amt})
#                                         if cmp_line.tax_amount > 0.0 and cmp_line.tax_id:
#                                             search_id.write({'tax':cmp_line.tax_amount * diff})
                                    else:
                                        vals_fee.update({'installment_id':last_record.id,
                                                                'product_id':cmp_line.product_id.id,
                                                                'name':cmp_line.type,
                                                                'base':cmp_line.product_amt*diff})
                                        if cmp_line.tax_amount > 0.0 and cmp_line.tax_id:
                                            bs_amt = vals_fee['base'] + (cmp_line.tax_amount*diff)
                                            vals_fee.update({'base':bs_amt})
                                        if vals_fee:
                                            self.env['fees.lines'].create(vals_fee)
                            last_record.late_fee = total*diff
#                         if current_date == date_object:
#                             for cmp_line in record.loan_type.loan_component_ids:
#                                 if cmp_line.type == 'late_fee':
#                                     lfee_total = self._get_late_fees_amount(record.loan_type, record.approve_amount, record.interest)
#                                     vals_fee.update({'installment_id':last_record.id,
#                                                                 'product_id':cmp_line.product_id.id,
#                                                                 'name':cmp_line.type,
#                                                                 'base':cmp_line.product_amt,})
#                                     if cmp_line.tax_id:
#                                         vals_fee.update({'tax':cmp_line.tax_amount})
#                                     if vals_fee:
#                                         self.env['fees.lines'].create(vals_fee)
#                                     last_record.late_fee = lfee_total
#             
    @api.multi
    def unlink(self):
        vouchers = self.env['account.voucher'].read(['state'])
        unlink_ids = []
        for t in vouchers:
            if t['state'] in ('draft', 'cancel'):
                unlink_ids.append(t['id'])
            else:
                raise exceptions.except_orm(_('Invalid action !'), _('Cannot delete vouchers(s) which are already opened or paid !'))
        res = super(AccountLoan, self).unlink()
        return res
    
    
    ##getting fees values basis of principle, interest and fees products ................
    def _get_late_fees_amount(self, loan_type, approve_amt, interest_amt):
        amt = 0.0
        if not loan_type.loan_component_ids:
            return amt
        sum_amt = 0.0
        flag = False
        flag1 = False
        global_list = []
        principal_list = []
        interest_list = []
        global_add1 = 0.0
        global_add2 = 0.0
        global_add3 = 0.0
        global_add4 = 0.0
        fees_list = []
        lfees_list = []
        
        global_dict = {}
        global_dict1 = {}
        internal_dict = {}
        for line in loan_type.loan_component_ids:
            if line.type == 'principal':
                flag = True
                if line.product_id.id not in principal_list:
                    principal_list.append(line.product_id.id)
            if line.type == 'int_rate':
                flag1 = True
                if line.product_id.id not in interest_list:
                    global_list.append(line.product_id.id)
                    interest_list.append(line.product_id.id)
            if line.type == 'fees':
                if line.product_id.id not in fees_list:
                    global_list.append(line.product_id.id)
                    fees_list.append(line.product_id.id)
                    global_dict.update({line.product_id.id:line})
            
            if line.type == 'late_fee':
                if line.product_id.id not in lfees_list:
                    lfees_list.append(line.product_id.id)
                    global_dict1.update({line.product_id.id:line})
                    
                
        for line in loan_type.loan_component_ids:
            if line.type == 'late_fee':
                tx_tot = 0.0
                if line.amount_select == 'percentage':
                    for product in line.amount_percentage_base:
                        sum_amt = 0.0
                        if product.id in principal_list: 
                            if line.amount_percentage and flag:
                                percent = line.amount_percentage * line.quantity
                                amt = (approve_amt * percent) / 100
                                sum_amt = sum_amt + amt
#                                 for tx_line in line.tax_id:
                                if line.tax_id:
                                    tx_tot = self.get_late_fee_tax_total(line.tax_id, sum_amt)
                                if tx_tot:
                                    if type(tx_tot) == dict:
                                        bse_tx = 0.0
                                        bse_tx = sum_amt - tx_tot.get('include')
                                        line.with_context({'inclsive':bse_tx}).write({'product_amt':bse_tx,'tax_amount':tx_tot.get('include')})
                                    else:
                                        line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                                        sum_amt = sum_amt + tx_tot
                                    line.write({'outstanding_product_amt':sum_amt})
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    internal_dict.update({line.product_id.id : sum_amt})
                                else:
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                                    internal_dict.update({line.product_id.id : sum_amt})
                                global_add1 = global_add1 + sum_amt
                                sum_amt = 0
                            
                        elif product.id in interest_list:
                            if line.amount_percentage and flag1:
                                percent = line.amount_percentage * line.quantity
                                amt1 = (interest_amt * line.amount_percentage) / 100
                                sum_amt = sum_amt + amt1
#                                 for tx_line in line.tax_id:
#                                     if tx_line.amount:
#                                         tx_tot = self.get_tax_total(tx_line, sum_amt)
                                if line.tax_id:
                                    tx_tot = self.get_late_fee_tax_total(line.tax_id, sum_amt)
                                if tx_tot:
                                    if type(tx_tot) == dict:
                                        bse_tx = 0.0
                                        bse_tx = sum_amt - tx_tot.get('include')
                                        line.with_context({'inclsive':bse_tx}).write({'product_amt':bse_tx,'tax_amount':tx_tot.get('include')})
                                    else:
                                        line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                                        sum_amt = sum_amt + tx_tot
                                    line.write({'outstanding_product_amt':sum_amt})
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    internal_dict.update({line.product_id.id : sum_amt})
                                else:
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                                    internal_dict.update({line.product_id.id : sum_amt})
                                global_add2 = global_add2 + sum_amt
                                sum_amt = 0
                                
                        elif product.id in global_dict:
                            amt_tot = 0.0
                            for o in global_dict[product.id]:
                                if o.amount_select == 'percentage':
#                                     for f in o.amount_percentage_base:
                                    if o.product_id.id in internal_dict:
                                        amt_tot = internal_dict[o.product_id.id]
#                                     internal_dict.update({line.product_id.id : sum_amt})
                                elif o.amount_select == 'fix':
                                    amt_tot = internal_dict[o.product_id.id]
#                                         amt_tot = amt_tot + (o.amount_fix * o.quantity)
                                              
                                percent1 = line.amount_percentage * line.quantity
                                amttotal = (amt_tot * percent1) / 100
                                sum_amt = amttotal
#                                 for tx_line in line.tax_id:
#                                     if tx_line.amount:
#                                         tx_tot = self.get_tax_total(tx_line, sum_amt)
                                if line.tax_id:
                                    tx_tot = self.get_late_fee_tax_total(line.tax_id, sum_amt)
                                if tx_tot:
                                    if type(tx_tot) == dict:
                                        bse_tx = 0.0
                                        bse_tx = sum_amt - tx_tot.get('include')
                                        line.with_context({'inclsive':bse_tx}).write({'product_amt':bse_tx,'tax_amount':tx_tot.get('include')})
                                    else:
                                        line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                                        sum_amt = sum_amt + tx_tot
                                        
                                    line.write({'outstanding_product_amt':sum_amt})
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    internal_dict.update({line.product_id.id : sum_amt})
                                else:
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                                    internal_dict.update({line.product_id.id : sum_amt})
                                global_add3 = global_add3 + sum_amt
                                sum_amt = 0
                                
                                
                        elif product.id in global_dict1:
                            amt_tot = 0.0
                            for o in global_dict1[product.id]:
                                if o.amount_select == 'percentage':
#                                     for f in o.amount_percentage_base:
                                    if o.product_id.id in internal_dict:
                                        amt_tot = internal_dict[o.product_id.id]
                                elif o.amount_select == 'fix':
                                    amt_tot = internal_dict[o.product_id.id]
#                                         amt_tot = amt_tot + (o.amount_fix * o.quantity)
                                              
                                percent1 = line.amount_percentage * line.quantity
                                amttotal = (amt_tot * percent1) / 100
                                sum_amt = amttotal
#                                 for tx_line in line.tax_id:
#                                     if tx_line.amount:
#                                         tx_tot = self.get_tax_total(tx_line, sum_amt)
                                if line.tax_id:
                                    tx_tot = self.get_late_fee_tax_total(line.tax_id, sum_amt)
                                if tx_tot:
                                    if type(tx_tot) == dict:
                                        bse_tx = 0.0
                                        bse_tx = sum_amt - tx_tot.get('include')
                                        line.with_context({'inclsive':bse_tx}).write({'product_amt':bse_tx,'tax_amount':tx_tot.get('include')})
                                    else:
                                        line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                                        sum_amt = sum_amt + tx_tot
                                    line.write({'outstanding_product_amt':sum_amt})
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    internal_dict.update({line.product_id.id : sum_amt})
                                else:
                                    if line.product_id.id in internal_dict:
                                        sum_amt = sum_amt + internal_dict[line.product_id.id]
                                    line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                                    internal_dict.update({line.product_id.id : sum_amt})
                                sum_amt = 0
                                
                elif line.amount_select == 'fix':
                    fix_amt = line.amount_fix * line.quantity
                    sum_amt = sum_amt + fix_amt
#                     for tx_line in line.tax_id:
#                         if tx_line.amount:
#                             tx_tot = self.get_tax_total(tx_line, sum_amt)
                    if line.tax_id:
                        tx_tot = self.get_late_fee_tax_total(line.tax_id, sum_amt)
                    if tx_tot:
                        if type(tx_tot) == dict:
                            bse_tx = 0.0
                            bse_tx = sum_amt - tx_tot.get('include')
                            line.with_context({'inclsive':bse_tx}).write({'product_amt':bse_tx,'tax_amount':tx_tot.get('include')})
                        else:
                            line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                            sum_amt = sum_amt + tx_tot
#                         line.write({'product_amt':sum_amt,'outstanding_product_amt':sum_amt, 'tax_amount':tx_tot})
#                         sum_amt = sum_amt + tx_tot
#                         line.write({'outstanding_product_amt':sum_amt})
                        if line.product_id.id in internal_dict:
                            sum_amt = sum_amt + internal_dict[line.product_id.id]
                        internal_dict.update({line.product_id.id : sum_amt})
                    else:
                        if line.product_id.id in internal_dict:
                            sum_amt = sum_amt + internal_dict[line.product_id.id]
                        line.write({'product_amt':sum_amt, 'outstanding_product_amt':sum_amt})
                        internal_dict.update({line.product_id.id : sum_amt})
                                  
                    global_add4 = global_add4 + sum_amt  
                    sum_amt = 0
                
                elif line.amount_select == 'code':
                    sum_amt = self.evaluate_python_code(line.amount_python_compute, approve_amt, interest_amt)
#                     for tx_line in line.tax_id:
#                         if tx_line.amount:
#                             tx_tot = self.get_tax_total(tx_line, sum_amt)
                    if line.tax_id:
                        tx_tot = self.get_late_fee_tax_total(line.tax_id, sum_amt)
                    if tx_tot:
                        
                        if type(tx_tot) == dict:
                            bse_tx = 0.0
                            bse_tx = sum_amt - tx_tot.get('include')
                            line.with_context({'inclsive':bse_tx}).write({'product_amt':bse_tx,'tax_amount':tx_tot.get('include')})
                        else:
                            line.write({'product_amt':sum_amt, 'tax_amount':tx_tot})
                            sum_amt = sum_amt + tx_tot
#                         line.write({'product_amt':sum_amt,'outstanding_product_amt':sum_amt, 'tax_amount':tx_tot})
#                         sum_amt = sum_amt + tx_tot
                        line.write({'outstanding_product_amt':sum_amt})
                        if line.product_id.id in internal_dict:
                            sum_amt = sum_amt + internal_dict[line.product_id.id]
                        internal_dict.update({line.product_id.id : sum_amt})
                    else:
                        if line.product_id.id in internal_dict:
                            sum_amt = sum_amt + internal_dict[line.product_id.id]
                        line.write({'product_amt':sum_amt,'outstanding_product_amt':sum_amt})
                        internal_dict.update({line.product_id.id : sum_amt})
                    sum_amt = 0
        
#         print (internal_dict,'late Feesss total')   
        if internal_dict:
            print ('to do list')
                
        total_all = sum(internal_dict.values())
        return total_all

class account_loan_disbursement(models.Model):
    _name = "account.loan.disbursement"
    _description = 'Collateral line'
    
    release_number = fields.Many2one('account.move','Release Number')
    name = fields.Many2one('res.partner','Partner Name',required=True)
    bill_date = fields.Date("Bill Date",required=True)
    disbursement_amt = fields.Float("Amount",required=True)
    loan_id = fields.Many2one('account.loan')

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _name = "account.move.line"
    

    acc_loan_id = fields.Many2one('account.loan', 'Customer')
    

class AccountLoanRepayment(models.Model):
    _name = "account.loan.repayment"
    _description = 'Account loan repayment'
    
    loan_id = fields.Many2one('account.loan')
    release_number = fields.Many2one('account.move','Release Number')
    name = fields.Many2one('res.partner','Partner Name',required=True)
    pay_date = fields.Date("Re-payment Date",required=True)
    amt = fields.Float("Amount",required=True)
    is_button_visible = fields.Boolean("Is Button Visible")
    
    
    @api.multi
    def loan_payment_cancel(self):
        today = datetime.datetime.today().date()
        if self.release_number:
            if self.release_number and self.release_number.state != 'posted':
                raise Warning('You can not cancel drafted Entries')
            
            reverse_changeslist = []
            
            payment_details_ids = self.env['payment.details'].search([('move_id','=', self.release_number.id)])
            for pd_line in payment_details_ids:
                is_prin = False
                is_int = False
                is_fee = False
                is_late_fee = False
                flag = False
                reverse_changeslist.append(pd_line.line_id)
                if pd_line.line_id:
                    pd_line.line_id.outstanding_prin += pd_line.prin_amt
                    # if datetime.datetime.strptime(pd_line.line_id.date, "%Y-%m-%d").date() <= today:
                    print("pd_line.line_id------------------> ",pd_line.line_id,today)
                    if pd_line.line_id.date <= today:
                        pd_line.line_id.due_principal += pd_line.prin_amt
                    else:
                        pd_line.line_id.due_principal = 0.00
                    if round(pd_line.line_id.outstanding_prin,2) == pd_line.line_id.capital:
#                         pd_line.line_id.due_principal = 0.0
                        is_prin = True
                if pd_line.line_id:
                    pd_line.line_id.outstanding_int += pd_line.int_amt
                    # if datetime.datetime.strptime(pd_line.line_id.date, "%Y-%m-%d").date() <= today:
                    if pd_line.line_id.date <= today:
                        pd_line.line_id.due_interest += pd_line.int_amt
                    else:
                        pd_line.line_id.due_interest = 0.00
                    if round(pd_line.line_id.outstanding_int,2) == pd_line.line_id.interest:
#                         pd_line.line_id.due_interest = 0.0
                        is_int = True
                if pd_line.line_id:
                    pd_line.line_id.outstanding_fees += pd_line.fees_amt
                    # if datetime.datetime.strptime(pd_line.line_id.date, "%Y-%m-%d").date() <= today:
                    if pd_line.line_id.date <= today:
                        pd_line.line_id.due_fees += pd_line.fees_amt
                    else:
                        pd_line.line_id.due_fees = 0.00
                    if round(pd_line.line_id.outstanding_fees,2) == pd_line.line_id.fees:
#                         pd_line.line_id.due_fees = 0.0
                        is_fee = True
                    for fee_line in pd_line.line_id.fee_lines:
                        if fee_line.name == 'fees':
                            fee_line.base_paid -= pd_line.base_fee_paid
                            fee_line.tax_paid -= pd_line.base_fee_tax_paid
                            if pd_line.base_fee_paid or pd_line.base_fee_tax_paid:
                                fee_line.is_paid = False
#                             fee_line.is_paid = False
                if pd_line.line_id:
                    pd_line.line_id.late_fee += pd_line.late_fee_amt
                    flag = True
                    if pd_line.line_id.late_fee == pd_line.line_id.late_fee:
                        is_late_fee = True
                    for fee_line in pd_line.line_id.fee_lines:
                        if fee_line.name == 'late_fee':
                            fee_line.base_paid -= pd_line.base_late_fee_amt
                            fee_line.tax_paid -= pd_line.base_late_fee_amt_tx
                            if fee_line.base_paid == 0.0 and fee_line.tax_paid == 0.0:
                                fee_line.is_paid = False
                
                if is_prin and is_int and is_fee and flag:
                    if is_late_fee:
                        pd_line.line_id.state = 'draft' 
                elif is_prin and is_int and is_fee:
                    pd_line.line_id.state = 'draft'
                else:
                    pd_line.line_id.state = 'open'
                    
            cancel_entry = self.release_number.button_cancel()
            if cancel_entry:
                self.is_button_visible = False
                payment_details_ids = self.env['payment.details'].search([('move_id','=', self.release_number.id)])
                for pyline in payment_details_ids:
                    pyline.state = 'cancel'
        return True
    
    @api.multi
    def delete_payment_line(self):
        for o in self:
            if o.release_number:
                payment_details_ids = self.env['payment.details'].search([('move_id','=', self.release_number.id)])
                for pyline in payment_details_ids:
                    pyline.unlink()
            if o.release_number:
                o.release_number.unlink()
            o.unlink()
        return True
        


