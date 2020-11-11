# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    category = fields.Char('Category')
    date_departure = fields.Date('Date Departure')
    level_study = fields.Char('Level Of Study')
    net_salary = fields.Char('Net Salary')
