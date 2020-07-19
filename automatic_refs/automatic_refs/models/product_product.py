import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    default_code = fields.Char(copy=False, required=False)
    company_id = fields.Many2one(related='product_tmpl_id.company_id', store=True)

    _sql_constraints = [
        ('code_uniq', 'unique (default_code, company_id)', 'The default code of the product must be unique!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """ Checks for the default_code method """
        if self.env['ir.config_parameter'].sudo().get_param('automatic_refs.product_default_code_type') == '1':
            for vals in vals_list:
                if not vals.get('default_code'):
                    vals['default_code'] = self.get_next_available_product_ref()
        return super(ProductProduct, self).create(vals_list)

    def get_next_available_product_ref(self):
        seq = self.env['ir.sequence'].sudo().search([
            ('prefix', '=', 'PROD')], limit=1)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name'            : 'Product sequence',
                'code'            : 'product.product',
                'implementation'  : 'standard',
                'prefix'          : 'PROD',
                'padding'         : 1,
                'number_increment': 1
            })
        while True:
            next_code = seq.sudo().next_by_id()
            if not self.search_count([('default_code', '=', next_code)]):
                return next_code
