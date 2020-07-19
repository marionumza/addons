

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
from odoo.exceptions import UserError, ValidationError
from datetime import date
import math
import json


class AccountLoanProofType(models.Model):
    _name="account.loan.proof.type"
    _description = "Account Loan Proof Type"

    name = fields.Char('Proof Type Name',size=64,required=True)
    shortcut = fields.Char("Shortcut",size=32,required=True)
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        acc_loan_proof_obj = self.env['account.loan.loantype']
        acc_proof_ids = []
#         if self._context and self._context.has_key('loan_type'):
        if self._context and 'loan_type' in self._context:
            for record in acc_loan_proof_obj.browse(int(self._context['loan_type'])).prooftypes:
                if record.name:
                    acc_proof_ids.append(record.id)
            args.append(['id', 'in', acc_proof_ids])
        return super(AccountLoanProofType, self)._search(args, offset=offset, limit=limit, order=order,count=count, access_rights_uid=access_rights_uid)


def _account_loan_proof_type_get(self):
#     obj = self.pool.get('account.loan.proof.type')
    ids = self.search([('name','ilike','')])
    res = self.read(['shortcut','name'])
    return [(r['name'], r['name']) for r in res]

class AccountLoanProof(models.Model):
    _name='account.loan.proof'
    _description = "Account Loan Proof"
    
    proof_name = fields.Char('Proof name',size=256,required=True)
    loan_id = fields.Many2one('account.loan', 'Loan', required=False)
    note = fields.Text('Proof Note')
    document = fields.Binary('Proof Document')
    type = fields.Many2one('account.loantype.prooflines','Type')
#     loan_type = fields.Many2one('account.loan.loantype',related='loan_id.loan_type',store=True) 
#     proof_domain = fields.Char('Proof Domain')
    
#         'type': fields.selection(_account_loan_proof_type_get,'Type',select=True),
# account.loantype.prooflines is  displayed
# account.loan.proof.type was used

    
    state =  fields.Selection(
        [
            ('draft','Draft'),
            ('apply','Under Verification'),
            ('done','Verified'),
            ('cancel','Cancel')
        ],'State', readonly=True, index=True,default = 'draft')
    
    
    @api.onchange('loan_id','type')
    def onchange_proofs(self):
        res = []
        if self.loan_id.loan_type.prooftypes:
            for o in self.loan_id.loan_type.prooftypes:
                res.append(o.id)
        return {'domain':{'type':[('id','in', res)]}}
            
    
#     @api.model
#     def default_get(self, fields):
#         res = super(AccountLoanProof, self).default_get(fields)
#         proof_types = self.env['account.loan.loantype'].browse(self._context.get('loan_type')).prooftypes
#         proofs = [line.id for line in proof_types]
#         res.update({'proof_domain':json.dumps([('id','in',proofs)])})
#         return res
        
    
#     @api.model
#     def create(self, vals):
#         print ("Valsssssssssss  ",vals)
# #         dfsdf
#         result = super(AccountLoanProof, self).create(vals)
#         print ("SELFFFFFFFF  ",self)
#         return result
    
#     _defaults = {
#         'state': lambda *a: 'draft',
#     }
    
#     def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
#         if context is None:
#             context = {}
#         ids = super(account_loan_proof, self).search(cr, uid, args, offset, limit, order, context, count)
#         if context.get('type'):
#             new_ids = []
#             proof_obj = self.pool.get('account.loan.proof')
#             proof_data = transport_obj.browse(cr, uid, context['type'])
#             point_ids = [point_id.id for point_id in transport_data.trans_point_ids]
#             args.append(('id','in',point_ids))
#         return ids
#     
    
  
#     @api.model
#     def default_get(self, fields):
#         data = self._default_get(fields)
#         print ("Dataaaaa ",data)
# #         for f in data.keys():
#         for f in list(data.keys()):
#             print ("Dataaaaaaa  ",f)
#             if f not in fields:
#                 del data[f]
#         return data
#     
#     @api.model
#     def _default_get(self,fields):
#         data = super(AccountLoanProof, self).default_get(fields)
# #         if self._context and self._context.has_key('loan_id'):
#         if self._context and 'loan_id' in self._context:
#             if not self._context['loan_id']:
#                 raise UserError(_('Please Save Record First'))
# #                 raise osv.except_osv(_('Error !'), _('Please Save Record First'))
#             data['loan_id'] = self._context['loan_id']
#         print ("Dataaaaaaa ",data)
#         return data

    @api.multi
    def apply_varification(self):
#         self.write({'state':'apply'})
        self.state = 'apply'
            
            
            
            
            

#     def apply_varification(self, cr, uid, ids,context = {}):
#         self.pool.get('account.loan.proof').write(cr,uid,ids,{'state':'apply'})
#         return True

    @api.multi
    def proof_varified(self):
#         if not self.name:
#             self.write({'name':self.name})
#         self.write({'state':'done'})
        self.state = 'done'
    
#     def proof_varified(self,cr,uid,ids,context = {}):
#         self.pool.get('account.loan.proof').write(cr,uid,ids,{'state':'done'})
#         return True
    @api.multi 
    def proof_canceled(self):
#         self.write({'state':'cancel'})
        self.state = 'cancel'
    
#     def proof_canceled(self,cr,uid,ids,context = {}):
#         self.pool.get('account.loan.proof').write(cr,uid,ids,{'state':'cancel'})
#         return True

