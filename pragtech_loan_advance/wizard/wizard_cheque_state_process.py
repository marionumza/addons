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
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
import time
# import wizard
#import netsvc
#import pooler
#from osv.orm import browse_record

draft2posted_form = """<?xml version="1.0"?>
<form string="Draft To Posted">
    <separator colspan="4" string="change State : Draft to Posted " />
</form>
"""

draft2posted_fields = {

}
def _draft2posted(self):
        # cheque_pool = pooler.get_pool(cr.dbname).get('account.loan.bank.cheque')
        cheque_pool = self.env['account.loan.bank.cheque']
        # wf_service = netsvc.LocalService("workflow")
        for o in cheque_pool:
            if o.state=='draft':
                cheque_pool.trg_validate('account.loan.bank.cheque', o.id, 'post_bank')
        return {}

class change_cheque_state(models.TransientModel):
    _description = "change_cheque_state"
    
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form',
                    'arch' : draft2posted_form,
                    'fields' : {},
                    'state' : [('end', 'Cancel'),('draft2posted', 'Draft To Posted') ]}
        },
        'draft2posted' : {
            'actions' : [],
            'result' : {'type' : 'action',
                    'action' : _draft2posted,
                    'state' : 'end'}
        },
    }
change_cheque_state()