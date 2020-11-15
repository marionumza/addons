# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date


class bed_transfer(models.Model):
    _name = 'bed.transfer'

    name = fields.Char("Name")
    date = fields.Datetime(string='Date')
    bed_from = fields.Char(string='Transfer From')
    bed_to = fields.Char(string='Transfer To')
    reason = fields.Text(string='Reason')
    inpatient_id = fields.Many2one('medical.inpatient.registration',string='Inpatient Id')
