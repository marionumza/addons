# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class medical_inpatient_diet(models.Model):
    _name = 'medical.inpatient.diet'

    diet_id = fields.Many2one('medical.diet.therapeutic',string='Diet',required=True)
    remarks = fields.Text(string=' Remarks / Directions ')
    medical_inpatient_registration_id = fields.Many2one('medical.inpatient.registration',string='Inpatient Id')


