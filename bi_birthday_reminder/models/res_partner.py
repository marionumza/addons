# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import SUPERUSER_ID
from odoo import api, fields, models, _
from odoo.http import request


class res_partner(models.Model):
    _inherit = "res.partner"

    birthdate = fields.Date(string='Date Of Birth')

    @api.model
    def _cron_birthday_reminder(self):
        su_id =self.env['res.partner'].browse(SUPERUSER_ID)
        for partner in self.search([]):
            if partner.birthdate:
                bdate =datetime.strptime(str(partner.birthdate),'%Y-%m-%d').date()
                today =datetime.now().date()
                if bdate != today:
                    if bdate.month == today.month:
                        if bdate.day == today.day:
                            if partner:
                                template_id = self.env['ir.model.data'].get_object_reference(
                                                                      'bi_birthday_reminder',
                                                                      'email_template_edi_birthday_reminder')[1]
                                email_template_obj = self.env['mail.template'].browse(template_id)
                                if template_id:
                                    values = email_template_obj.generate_email(partner.id, fields=None)
                                    values['email_from'] = su_id.email
                                    values['email_to'] = partner.email
                                    values['res_id'] = True
                                    values['author_id'] = self.env['res.users'].browse(request.env.uid).partner_id.id
                                    mail_mail_obj = self.env['mail.mail']
                                    print('\n\n\n',values,'\n\n\n')
                                    msg_id = mail_mail_obj.sudo().create(values)
                                    if msg_id:
                                        mail_mail_obj.sudo().send([msg_id])

        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
