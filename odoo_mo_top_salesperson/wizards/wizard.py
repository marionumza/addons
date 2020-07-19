# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Wizard(models.TransientModel):
    _name = 'odoo_mo.top_salesperson'

    date_from = fields.Date(string="Date From",required=True)
    date_to = fields.Date(string="Date From",required=True)
    sales_orders = fields.Many2many(comodel_name="sale.order", relation="top_salesperson_sales",
                                        string="Sales Orders")
    salesperson = fields.Many2many(comodel_name="res.users", relation="top_salesperson_partner", string="Salesperson")
    no_of_salesperson = fields.Integer(string="Number Of Salesperson", required=True, default=1)
    lines = fields.One2many(comodel_name="odoo_mo.top_salesperson_template", inverse_name="wiz_id", string="Data",
                            readonly=True)

    def _get_lines(self):
        where="date(date_order)>=\'"+str(self.date_from)+"\'"
        where+=" and date(date_order)<=\'"+str(self.date_to)+"\'"
        where+=" and state='sale'"
        if self.salesperson:
            if len(self.salesperson)>1:
                where += " and user_id in " + str(tuple(self.salesperson.ids))
            else:
                where += " and user_id = " + str(self.salesperson.ids[0])

        if self.sales_orders:
            if len(self.sales_orders)>1:
                where += " and id in " + str(tuple(self.sales_orders.ids))
            else:
                where += " and id = " + str(self.sales_orders.ids[0])
        query = """
            select  user_id,sum(amount_total) as amount 
            from sale_order 
            where {where}
            group by user_id order by amount desc
            limit {no_of_salesperson}
            """.format(no_of_salesperson=self.no_of_salesperson,where=where)
        self._cr.execute(query)
        lines = self._cr.dictfetchall()
        return lines


    def preview(self):
        self.lines = [(5, 0, 0)]
        line_list=[]
        lines=self._get_lines()
        for line in lines:
            line_list.append((0,0,{
                'salesperson':line.get('user_id'),
                'amount':line.get('amount')
            }))
        self.lines=line_list
        return {
            'type': 'ir.actions.act_window',
            'res_model': "odoo_mo.top_salesperson",
            'res_id': self.id,
            'view_mode': 'form,tree',
            'name': 'Top SalesPerson',
            'target': 'new'
        }

    def dynamic_view(self):
        lines = self._get_lines()
        for line in lines:
            line['salesperson_name']=self.env['res.users'].search([('id','=',line.get('user_id'))],limit=1).name
        return {
            'name': "Top Salesperson",
            'type': 'ir.actions.client',
            'tag': 'top_salesperson_view',
            'lines': lines,
        }

    def print_pdf(self):
        data={}
        lines = self._get_lines()
        data['lines']=lines
        return self.env.ref('odoo_mo_top_salesperson.odoo_mo_top_salesperson_action').report_action([], data=data)

    def print_excel(self):
        data = {}
        lines = self._get_lines()
        data['lines'] = lines
        return self.env.ref('odoo_mo_top_salesperson.odoo_mo_top_salesperson_action_xlsx').report_action([],data=data)


class Template(models.TransientModel):
    _name = 'odoo_mo.top_salesperson_template'

    salesperson = fields.Many2one(comodel_name="res.users", string="Salesperson", readonly=True)

    amount = fields.Float(string="Amount", readonly=True)

    wiz_id = fields.Many2one(comodel_name="odoo_mo.top_salesperson")
