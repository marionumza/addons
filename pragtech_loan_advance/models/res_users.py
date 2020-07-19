from odoo import models

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    def get_logged_name(self):
        user = self.env['res.users'].browse(self._context.get('uid'))
        name = ''
        if user:
            name = user.partner_id.display_name if user.partner_id else user.name
        return name
        