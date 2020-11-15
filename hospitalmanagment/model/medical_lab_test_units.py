# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
# classes under cofigration menu of laboratry 


class medical_lab_test_units(models.Model):

    _name = 'medical.lab.test.units'
    
    name = fields.Char('Name', required = True)
    code  =  fields.Char('Code')


