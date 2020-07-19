from odoo import fields, models, api, _

class AccountVoucher(models.Model):
    _inherit = 'account.voucher'
    
#     loan_id = fields.Many2one("Loan reference")
AccountVoucher()