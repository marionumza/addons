from odoo import models, api, fields, _,SUPERUSER_ID
import json
from datetime import datetime
# import operator


class account_loan_dashboard(models.Model):
    _name = 'account.loan.dashboard'
    _description = "Account Loan dashboard"
    
    @api.one
    def _get_count(self):
        '''
            Compute method used to get data for multiple fields
        '''
        loan_obj = self.env['account.loan']
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            self._cr.execute('select count(id) from account_loan where company_id={}'.format(self.env.user.company_id.id))
            loan_count1 = self._cr.fetchone()
            if loan_count1:
                loan_count = loan_count1[0]
            else:
                loan_count = 0
#             loan_count = loan_obj.sudo().search([('company_id','=',self.env.user.company_id.id)])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='draft'".format(self.env.user.company_id.id))
            new_loan1 = self._cr.fetchone()
            if new_loan1:
                new_loan = new_loan1[0]
            else:
                new_loan = 0
#             new_loan = loan_obj.sudo().search([('state', '=', 'draft'),('company_id','=',self.env.user.company_id.id)])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='done'".format(self.env.user.company_id.id))
            loan_done_count1 = self._cr.fetchone()
            if loan_done_count1:
                loan_done_count = loan_done_count1[0]
            else:
                loan_done_count = loan_done_count1[0]
                
#             loan_done_count = loan_obj.sudo().search([('state', '=', 'done'),('company_id','=',self.env.user.company_id.id)])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='apply'".format(self.env.user.company_id.id))
            loan_sanctioned_count1 = self._cr.fetchone()
            if loan_sanctioned_count1:
                loan_sanctioned_count = loan_sanctioned_count1[0]
            else:
                loan_sanctioned_count = loan_sanctioned_count1[0]
#             loan_sanctioned_count = loan_obj.sudo().search([('state', '=', 'apply'),('company_id','=',self.env.user.company_id.id)])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='approved'".format(self.env.user.company_id.id))
            loan_disbursed_count1 = self._cr.fetchone()
            if loan_disbursed_count1:
                loan_disbursed_count = loan_disbursed_count1[0]
            else:
                loan_disbursed_count = loan_disbursed_count1[0]
#             loan_disbursed_count = loan_obj.sudo().search([('state', '=', 'approved'),('company_id','=',self.env.user.company_id.id)])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='partial'".format(self.env.user.company_id.id))
            loan_partial_count1 = self._cr.fetchone()
            if loan_partial_count1:
                loan_partial_count = loan_partial_count1[0]
            else:
                loan_partial_count = loan_partial_count1[0]
#             loan_partial_count = loan_obj.sudo().search([('state', '=', 'partial'),('company_id','=',self.env.user.company_id.id)])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='cancel'".format(self.env.user.company_id.id))
            loan_cancel_count1 = self._cr.fetchone()
            if loan_cancel_count1:
                loan_cancel_count = loan_cancel_count1[0]
            else:
                loan_cancel_count = loan_cancel_count1[0]
#             loan_cancel_count = loan_obj.sudo().search([('state', '=', 'cancel'),('company_id','=',self.env.user.company_id.id)])
        else:
            self._cr.execute('select count(id) from account_loan')
            loan_count1 = self._cr.fetchone()
            if loan_count1:
                loan_count = loan_count1[0]
            else:
                loan_count = 0
#             loan_count = loan_obj.sudo().search([])\
            self._cr.execute("select count(id) from account_loan where company_id={} and state='draft'".format(self.env.user.company_id.id))
            new_loan1 = self._cr.fetchone()
            if new_loan1:
                new_loan = new_loan1[0]
            else:
                new_loan = 0
#             new_loan = loan_obj.sudo().search([('state', '=', 'draft')])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='done'".format(self.env.user.company_id.id))
            loan_done_count1 = self._cr.fetchone()
            if loan_done_count1:
                loan_done_count = loan_done_count1[0]
            else:
                loan_done_count = loan_done_count1[0]
#             loan_done_count = loan_obj.sudo().search([('state', '=', 'done')])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='apply'".format(self.env.user.company_id.id))
            loan_sanctioned_count1 = self._cr.fetchone()
            if loan_sanctioned_count1:
                loan_sanctioned_count = loan_sanctioned_count1[0]
            else:
                loan_sanctioned_count = loan_sanctioned_count1[0]
#             loan_sanctioned_count = loan_obj.sudo().search([('state', '=', 'apply')])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='approved'".format(self.env.user.company_id.id))
            loan_disbursed_count1 = self._cr.fetchone()
            if loan_disbursed_count1:
                loan_disbursed_count = loan_disbursed_count1[0]
            else:
                loan_disbursed_count = loan_disbursed_count1[0]
#             loan_disbursed_count = loan_obj.sudo().search([('state', '=', 'approved')])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='partial'".format(self.env.user.company_id.id))
            loan_partial_count1 = self._cr.fetchone()
            if loan_partial_count1:
                loan_partial_count = loan_partial_count1[0]
            else:
                loan_partial_count = loan_partial_count1[0]
#             loan_partial_count = loan_obj.sudo().search([('state', '=', 'partial')])
            self._cr.execute("select count(id) from account_loan where company_id={} and state='cancel'".format(self.env.user.company_id.id))
            loan_cancel_count1 = self._cr.fetchone()
            if loan_cancel_count1:
                loan_cancel_count = loan_cancel_count1[0]
            else:
                loan_cancel_count = loan_cancel_count1[0]
#             loan_cancel_count = loan_obj.sudo().search([('state', '=', 'cancel')])
 
        self.loan_count = loan_count
        self.loan_done_count = loan_done_count
        self.loan_sanctioned_count = loan_sanctioned_count
        self.loan_disbursed_count = loan_disbursed_count
        self.loan_partial_count = loan_partial_count
        self.loan_cancel_count = loan_cancel_count
        self.new_loan = new_loan
        
    @api.one
    def _get_total_amount(self):
        date_new = datetime.now()
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            loan_obj = self.env['account.loan'].sudo().search([('company_id','=',self.env.user.company_id.id)])
        else:
            loan_obj = self.env['account.loan'].sudo().search([])
        total = 0.00
        total_out = 0.00
        for loan in loan_obj:
            cur_id = None
            if loan.journal_disburse_id:
                if loan.journal_disburse_id.currency_id:
                    cur_id = loan.journal_disburse_id.currency_id
                else:
                    cur_id = loan.journal_disburse_id.company_id.currency_id
            
            for dis in loan.disbursement_details:
                if dis.release_number.state == 'posted':
                    for line in dis.release_number.line_ids:
                        total += line.credit
            for out in loan.installment_id:
                out_total = out.outstanding_prin + out.outstanding_fees + out.outstanding_int
                
                if cur_id:
                    total_out += loan.company_id.currency_id.with_context(date=date_new).compute(out_total, cur_id)
                else:
                    total_out += out_total
               
#         print("At the end=============",total_out,self.company_id)
        currency_name = self.env.user.company_id.currency_id.name
        self.total_amt = str(round(total,2)) + ' (' + currency_name + ')'
        self.total_out_amt = str(round(total_out,2)) + ' (' + currency_name + ')'
            
    @api.one
    def _kanban_dashboard_graph(self):
        self.kanban_dashboard_graph = json.dumps(self.get_bar_graph_datas())
    
    @api.one
    def _sector_graph(self):
        self.sector_graph = json.dumps(self.get_sector_datas())
        
    @api.one
    def _delinquency_graph(self):
        self.delinquency_graph = json.dumps(self.get_delinquency_datas())
    
    @api.one
    def _out_graph(self):
        self.outstanding_graph = json.dumps(self.get_out_datas())
    
    sector_graph = fields.Text(compute='_sector_graph')
    delinquency_graph = fields.Text(compute='_delinquency_graph')
    outstanding_graph = fields.Text(compute='_out_graph')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    color = fields.Integer(string='Color Index')
    name = fields.Char(string="Name")
    loan_count = fields.Integer(compute='_get_count')
    loan_done_count = fields.Integer(compute='_get_count')
    loan_sanctioned_count = fields.Integer(compute='_get_count')
    loan_disbursed_count = fields.Integer(compute='_get_count')
    loan_partial_count = fields.Integer(compute='_get_count')
    loan_cancel_count = fields.Integer(compute='_get_count')
    new_loan = fields.Integer(compute='_get_count')
    delinquency_percent = fields.Float(compute='_get_percent')
    is_group = fields.Boolean()
#     company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    total_amt = fields.Char(compute='_get_total_amount')
    total_out_amt = fields.Char(compute='_get_total_amount')
    
    def _graph_title_and_key(self):
        return ['', _('Loan: Disbursed Amount')]
    
    @api.multi
    def get_bar_graph_datas(self):
        '''
            Called from Compute method to calculate data for Loan Details tab
            params : self
            return : a list of dictionary that needs to be dumped into JSON format
        '''
        data = []
        past_total = 0.00
        present = 0.00
        ps1 = 0.00
        ps2 = 0.00
        ps3 = 0.00
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            loan_obj = self.env['account.loan'].sudo().search([('company_id','=',self.env.user.company_id.id)])
        else:
            loan_obj = self.env['account.loan'].sudo().search([])
        dt = datetime.today()
        for loan in loan_obj:
            for dis in loan.disbursement_details:
                print("dis.bill_date-------------------> ",dt.year,type(dt.year),type(dis.bill_date),dis.bill_date)
                if str(dt.year) in str(dis.bill_date):
                    if dis.release_number.state == 'posted':
                        for line in dis.release_number.line_ids:
                            present += line.credit
                elif str(dt.year - 1) in str(dis.bill_date):
                    if dis.release_number.state == 'posted':
                        for line in dis.release_number.line_ids:
                            ps1 += line.credit
                elif str(dt.year - 2) in str(dis.bill_date):
                    if dis.release_number.state == 'posted':
                        for line in dis.release_number.line_ids:
                            ps2 += line.credit
                elif str(dt.year - 3) in str(dis.bill_date):
                    if dis.release_number.state == 'posted':
                        for line in dis.release_number.line_ids:
                            ps3 += line.credit
                else:
                    if dis.release_number.state == 'posted':
                        for line in dis.release_number.line_ids:
                            past_total += line.credit
                    
        data = [{'value': past_total, 'label': 'Past'},
                {'value': ps3, 'label': str(dt.year - 3)},
                {'value': ps2, 'label': str(dt.year - 2)},
                {'value': ps1, 'label': str(dt.year - 1)},
                {'value': present, 'label': 'This Year'}]
        
        [graph_title, graph_key] = self._graph_title_and_key()
        return [{'values': data, 'title': graph_title, 'key': graph_key}]
    
    @api.multi
    def get_out_datas(self):
        '''
            Called from Compute method to calculate data for outstanding tab
            params : self
            return : a list of dictionary that needs to be dumped into JSON format
        '''
        date_new = datetime.now()
        pri = 0.00
        intr = 0.00
        fees = 0.00
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            loan_obj = self.env['account.loan'].sudo().search([('company_id','=',self.env.user.company_id.id)])
        else:
            loan_obj = self.env['account.loan'].sudo().search([])
        for loan in loan_obj:
            cur_id = None
            if loan.journal_disburse_id:
                if loan.journal_disburse_id.currency_id:
                    cur_id = loan.journal_disburse_id.currency_id
                else:
                    cur_id = loan.journal_disburse_id.company_id.currency_id
            for ins in loan.installment_id:
                if cur_id:
                    pri += loan.company_id.currency_id.with_context(date=date_new).compute(ins.outstanding_prin, cur_id)
                    intr += loan.company_id.currency_id.with_context(date=date_new).compute(ins.outstanding_int, cur_id)
                    fees += loan.company_id.currency_id.with_context(date=date_new).compute(ins.outstanding_fees, cur_id)
                else:
                    pri += ins.outstanding_prin
                    intr += ins.outstanding_int
                    fees += ins.outstanding_fees
                
        data = [{'value': pri, 'label': 'Principle'},
                {'value': intr, 'label': 'Interest'},
                {'value': fees, 'label': 'Fees'}]
        return [{'values': data, 'title': '', 'key': _('Outstanding Amount')}]
    
    @api.multi
    def get_sector_datas(self):
        '''
            Called from Compute method to calculate data for sector tab
            params : self
            return : a list of dictionary that needs to be dumped into JSON format
        '''
        data = []
        sec_dict = {}
        t1 = t2 = t3 = ('Rest', 0.00)
        so = ('Rest', 0.00)
        rest_dict = {'Rest':0.00, 'Undefined':0.00}
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            loan_obj = self.env['account.loan'].sudo().search([('company_id','=',self.env.user.company_id.id)])
        else:
            loan_obj  = self.env['account.loan'].sudo().search([])
        
        for loan in loan_obj:
            dis_tot = 0.00
            for dis in loan.disbursement_details:
                if dis.release_number.state == 'posted':
                    for line in dis.release_number.line_ids:
                        dis_tot += line.credit
#                 dis_tot += dis.disbursement_amt
            if loan.partner_id.industry_id:
                if loan.partner_id.industry_id.name in sec_dict:
                    sec_dict[loan.partner_id.industry_id.name] += dis_tot
                else:
                    sec_dict.update({loan.partner_id.industry_id.name : dis_tot})
            else:
                rest_dict['Undefined'] += dis_tot
            
            so = sorted(sec_dict.items(), key=lambda kv: kv[1])
            
            if len(so) > 0:
                t1 = so[-1]
            if len(so) > 1:
                t2 = so[-2]
            if len(so) > 2:
                t3 = so[-3]
            
            data = [{'value':t1[1], 'label':t1[0]},
                    {'value':t2[1], 'label':t2[0]},
                    {'value':t3[1], 'label':t3[0]}]
        if len(so) > 3:
            for item in so[:-3]:
                rest_dict['Rest'] += item[1]
        
        data.append({'value':rest_dict['Rest'], 'label':'Rest'})
        data.append({'value':rest_dict['Undefined'], 'label':'Undefined'})
        
        [graph_title, graph_key] = self._graph_title_and_key()
        return [{'values': data, 'title': graph_title, 'key': graph_key}]
        
    
    def get_amount_dict(self):
        '''
            This method is used to get disbursed amount and principal amount
            for delinquency rate tab
            params : self
            return : a dictionary that contains total disbursed amount and total principal due
        '''
        date_new = datetime.now()
        pri = 0.00
        disb = 0.00
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            loan_obj = self.env['account.loan'].sudo().search([('state','in',['partial','approved','done']),('company_id','=',self.env.user.company_id.id)])
        else:
            loan_obj = self.env['account.loan'].sudo().search([('state','in',['partial','approved','done'])])
        for loan in loan_obj:
            for ins in loan.installment_id:
                if ins.date:
                    if datetime.strptime(str(ins.date), "%Y-%m-%d") <= date_new:
                        pri += ins.due_principal
                    disb += ins.outstanding_prin
#             for dis in loan.disbursement_details:
#                 if dis.release_number.state == 'posted':
#                     for line in dis.release_number.line_ids:
#                         disb += line.credit
        return {'disbursed':disb,'principal':pri}
    
    @api.multi
    def get_delinquency_datas(self):
        '''
            Called from Compute method to calculate data for delinquency tab
            params : self
            return : a list of dictionary that needs to be dumped into JSON format
        '''
        amount = self.get_amount_dict()
        
        data = [{'value': amount['principal'], 'label': 'Total Principal Due'},
                {'value': amount['disbursed'], 'label':'Total Principal Outstanding'}
                ]
        return [{'values': data, 'title': '', 'key': _('Principal Amount')}]
    
    
    @api.multi
    def _get_percent(self):
        '''
            a compute method that calculates the delinquency rate percentage and assigns 
            to delinquency_percent
            params : self
        '''
        amount = self.get_amount_dict()
        for rec in self:
            try:
                rec.delinquency_percent = round((amount['principal']/amount['disbursed'])*100,2)
            except ZeroDivisionError:
                rec.delinquency_percent = 0
                
                
                
                
                