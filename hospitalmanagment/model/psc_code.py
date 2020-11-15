# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class psc_code(models.Model):
    _name  = 'psc.code'
    
    name = fields.Char('Code', required =True) 
    description = fields.Text('Long Text', required =True)


