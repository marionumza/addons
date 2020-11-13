# -*- coding: utf-8 -*-

from odoo.addons.turno_online.helpers import functions
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class turnoschedule(models.Model):
    _name = 'pronexo.turno.schedule'
    _order = 'user_id, day, schedule'
    _description = "turnos schedule"
    
    @api.model
    def _get_week_days(self):
        return [
            ('0', _('Monday')),
            ('1', _('Tuesday')),
            ('2', _('Wednesday')),
            ('3', _('Thursday')),
            ('4', _('Friday')),
            ('5', _('Saturday')),
            ('6', _('Sunday'))
        ]

    user_id = fields.Many2one('res.users', string='User', required=True)
    day = fields.Selection(selection=_get_week_days, default='0', string="Day", required=True)
    schedule = fields.Float('schedule', required=True)

    @api.constrains('schedule')
    def _schedule_validation(self):
        for schedule in self:
            if functions.float_to_time(schedule.schedule) < '00:00' or functions.float_to_time(schedule.schedule) > '23:59':
                raise ValidationError(_('The schedule value must be between 0:00 and 23:59!'))
