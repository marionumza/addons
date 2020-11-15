# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class medical_diet_belief(models.Model):
    _name = 'medical.diet.belief'

    code = fields.Char(string='Code',required=True)
    description = fields.Text(string='Description',required=True)
    name = fields.Char(string='Belief')


