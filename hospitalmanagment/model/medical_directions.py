# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class medical_directions(models.Model):
    _name = 'medical.directions'
    _rec_name = 'medical_directions_pathology_id'

    medical_directions_pathology_id = fields.Many2one('medical.pathology','Procedure')
    patient_evaluation_id = fields.Many2one('medical.patient.evaluation','Patient Evaluation')
    comments = fields.Char('Comments')

