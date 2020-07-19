import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_default_code = fields.Selection([
        ('0', 'Manual'),
        ('1', 'Auto Increment'),
    ], 'Internal Reference', config_parameter='automatic_refs.product_default_code_type', default='1')

    partner_ref = fields.Selection([
        ('0', 'Manual'),
        ('1', 'Auto Increment'),
    ], 'Partner Reference', config_parameter='automatic_refs.partner_ref_type', default='1')
