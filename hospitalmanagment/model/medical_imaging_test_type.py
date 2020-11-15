# # -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class medical_imaging_test_type(models.Model):
    _name = 'medical.imaging.test.type'

    name = fields.Char('Name', required = True)
    code = fields.Char('Code', required = True)


