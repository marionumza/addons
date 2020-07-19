from odoo import fields, models, api, _

class Lead(models.Model):
    _inherit = 'crm.lead'

    go_to_loan_app = fields.Boolean(string='Go to Loan Application',default=False)
    loan_id = fields.Many2one('account.loan')

    loan_count = fields.Integer(
        string="Number of Loans",
        compute='_compute_loan_count')

    def _compute_loan_count(self):
        '''
            Calculates the count of the Loans
        '''
        loan_data = self.env['account.loan'].search([('lead_id', '=', self.id)])
        self.loan_count = len(loan_data)

    def action_view_loan(self):
        '''
            This function will show those loans which against the active lead
        '''
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Loan Applications',
            'res_model': 'account.loan',
        }
        action.update({
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
        })
        return action

    @api.multi
    def action_set_won(self):
        '''
            This function gets invoked on the Mark Won button
        '''
        res = super(Lead, self).action_set_won()
        if self:
            self.go_to_loan_app = True
        return res

    @api.multi
    def action_set_lost(self):
        '''
            This function gets invoked on the Mark Lost Button
        '''
        res = super(Lead, self).action_set_lost()
        if self:
            self.go_to_loan_app = False
        return res

    @api.multi
    def action_open_loan(self):
        '''
            Opens the form view of account.loan to create it,and pass on the context fields defined
        '''
        if self.partner_id:
            view_id = self.env.ref('pragtech_loan_advance.account_loan_form').id
            return {
                'name': _('Loan Application'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'account.loan',
                'view_id': view_id,
                'views': [(view_id, 'form')],
                'target': 'current',
                'context': {
                    'default_partner_id': self.partner_id.id,
                    'default_req_amt': self.planned_revenue,
                    'default_lead_id':self.id
                }
            }
