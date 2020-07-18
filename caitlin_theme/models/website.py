from odoo import models, api, fields, _


class Website(models.Model):
    _inherit = 'website'

    @api.multi
    def get_blogs(self):
        blog_ids = self.env['blog.post'].search(
            [('website_published', '=', True)])
        return blog_ids
