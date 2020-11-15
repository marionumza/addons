# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class medical_imaging_test(models.Model):
    _name = 'medical.imaging.test'

    name = fields.Char('Name', required = True)
    code = fields.Char('Code', required = True)
    product_id = fields.Many2one('product.product','Service', required = True)
    test_type_id = fields.Many2one('medical.imaging.test.type','Type', required = True)


