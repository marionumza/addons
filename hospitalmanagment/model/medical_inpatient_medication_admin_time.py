# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date,datetime


class medical_inpatient_medication_admin_time(models.Model):
    _name = 'medical.inpatient.medication.admin.time'

    admin_time = fields.Datetime(string='Date')
    dose = fields.Float(string='Dose')
    remarks = fields.Text(string='Remarks')
    medical_inpatient_admin_time_id = fields.Many2one('medical.physician',string='Health Professional')
    dose_unit = fields.Many2one('medical.dose.unit',string='Dose Unt')
    medical_inpatient_admin_time_medicament_id = fields.Many2one('medical.inpatient.medication',string='Admin Time')


