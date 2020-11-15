# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class medical_diet_therapeutic(models.Model):
    _name = 'medical.diet.therapeutic'

    name = fields.Char(string='Diet Type',required=True)
    code = fields.Char(string='Code',required=True)
    description = fields.Text(string='Description',required=True)


