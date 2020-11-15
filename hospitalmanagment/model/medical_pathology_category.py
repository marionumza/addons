# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class medical_pathology_category(models.Model):
    _name = 'medical.pathology.category'
    
    name = fields.Char(string="Category Name",required=True)
    active = fields.Boolean(string="Active" , default = True)
    parent_id = fields.Many2one('medical.pathology.category', string="Parent Category")

