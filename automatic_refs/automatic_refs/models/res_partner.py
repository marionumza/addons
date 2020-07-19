import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = "res.partner"

    ref = fields.Char(copy=False)

    _sql_constraints = [
        ('ref_uniq', 'unique(ref, company_id)', 'The partner reference must be unique!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env['ir.config_parameter'].sudo().get_param('automatic_refs.partner_ref_type') == '1':
            for vals in vals_list:
                if not vals.get('ref'):
                    vals['ref'] = self.get_next_available_customer_ref()
        return super(Partner, self).create(vals_list)

    def get_next_available_customer_ref(self):
        seq = self.env['ir.sequence'].sudo().search([('prefix', '=', 'PART')], limit=1)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name'            : 'Partner sequence',
                'code'            : 'res.partner',
                'implementation'  : 'standard',
                'prefix'          : 'PART',
                'padding'         : 1,
                'number_increment': 1
            })
        while True:
            next_code = seq.next_by_id()
            if not self.search_count([('ref', '=', next_code)]):
                return next_code
