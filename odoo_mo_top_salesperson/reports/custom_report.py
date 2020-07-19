#!/usr/bin/env python
# -*- coding: utf-8 -*-

from odoo import models, fields
import math


class Report(models.AbstractModel):
    _name = 'report.odoo_mo_top_salesperson.top_temp'

    def _get_report_values(self, docids, data=None):
        lines=data.get('lines',[])
        docargs = {
            'lines': lines,
        }
        return docargs



class TopCustomersXlsx(models.AbstractModel):
    _name = 'report.odoo_mo_top_salesperson.xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook,data,wiz_id):
        lines=data.get('lines',[])
        report_name = "Top SalesPerson"
        # One sheet by partner
        sheet = workbook.add_worksheet(report_name[:31])
        bold = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 12})
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 25)
        sheet.set_column('C:C', 25)
        sheet.write(0, 0, 'No', bold)
        sheet.write(0, 1, 'SalesPerson', bold)
        sheet.write(0, 2, 'Amount', bold)
        row=1
        i=1
        for line in lines:
            sheet.write(row, 0,i, bold)
            sheet.write(row,1, self.env['res.users'].search([('id','=',line.get('user_id'))],limit=1).name, bold)
            sheet.write(row,2,line.get('amount'), bold)
            row+=1
            i+=1







