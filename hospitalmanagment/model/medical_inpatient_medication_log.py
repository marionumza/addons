# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date,datetime


class medical_inpatient_medication_log(models.Model):
    _name = 'medical.inpatient.medication.log'

    admin_time = fields.Datetime(string='Date',readonly=True)
    dose = fields.Float(string='Dose')
    remarks = fields.Text(string='Remarks')
    medical_inpatient_medication_log_id = fields.Many2one('medical.physician',string='Health Professional',readonly=True)
    medical_dose_unit_id = fields.Many2one('medical.dose.unit',string='Dose Unt')
    medical_inaptient_log_medicament_id = fields.Many2one('medical.inpatient.medication',string='Log History')


