# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class pet_type(models.Model):
    _name = 'pet.type'

    name = fields.Char('Name', required = True)
    code = fields.Char('Code')


