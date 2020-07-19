from odoo import fields, models, api, _

class LoanExtended(models.TransientModel):
    _name = "loan.extended"
    _description = "Extended loan period"

    date = fields.Date('Date', default=fields.Date.today())
    period_id = fields.Many2one('loan.installment.period', 'Loan Period')

    @api.multi
    def extend_period(self):
        for loan in self._context['active_ids']:
            loan_id = self.env['account.loan'].browse(loan)
            if loan_id.loan_period.id != self.period_id.id:
                loan_id.loan_period = self.period_id.id
                loan_id.total_installment = self.period_id.period

                wizard_id = self.env['loan.disbursement.wizard'].create({
                    'disbursement_amt': loan_id.loan_amount,
                    'name': 'Extended Period',
                    'date': self.date,
                })
                wizard_id.with_context({'is_extended': True, 'active_id': loan_id.id, 'date': self.date}).approve_loan()

        return