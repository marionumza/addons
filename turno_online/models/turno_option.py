# -*- coding: utf-8 -*-

from odoo.addons.turno_online.helpers import functions
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class turnosOption(models.Model):
    _name = 'pronexo.turno.option'
    _description = 'turnos option'

    name = fields.Char(string='turnos option', required=True)
    duration = fields.Float('Duration', required=True)

    @api.constrains('duration')
    def _duration_validation(self):
        for option in self:
            if functions.float_to_time(option.duration) < '00:05' or functions.float_to_time(option.duration) > '08:00':
                raise ValidationError(_('The duration value must be between 0:05 and 8:00!'))

