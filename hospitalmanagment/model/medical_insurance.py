# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class medical_insurance(models.Model):
    _name = 'medical.insurance'
    _rec_name = 'insurance_compnay_id'

    number = fields.Char('Number')
    medical_insurance_partner_id = fields.Many2one('res.partner','Owner',required=True)
    patient_id = fields.Many2one('res.partner', 'Owner')
    type =  fields.Selection([('state','State'),('private','Private'),('labour_union','Labour Union/ Syndical')],'Insurance Type')
    member_since= fields.Date('Member Since')
    insurance_compnay_id = fields.Many2one('res.partner',domain=[('is_insurance_company','=',True)],string='Insurance Compnay')
    category = fields.Char('Category')
    notes= fields.Text('Extra Info')
    member_exp = fields.Date('Expiration Date')
    medical_insurance_plan_id = fields.Many2one('medical.insurance.plan','Plan')

