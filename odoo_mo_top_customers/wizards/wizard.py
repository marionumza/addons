# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Wizard(models.TransientModel):
    _name = 'odoo_mo.top_customers'

    date_from = fields.Date(string="Date From",required=True)
    date_to = fields.Date(string="Date From",required=True)
    sales_orders = fields.Many2many(comodel_name="sale.order", relation="top_customers_sales",
                                        string="Sales Orders")
    customers = fields.Many2many(comodel_name="res.partner", relation="top_customers_partner", string="Vendors",domain=[('customer_rank','=',1)])
    no_of_customers = fields.Integer(string="Number Of Customers", required=True, default=1)
    lines = fields.One2many(comodel_name="odoo_mo.top_customers_template", inverse_name="wiz_id", string="Data",
                            readonly=True)

    def _get_lines(self):
        where="date(date_order)>=\'"+str(self.date_from)+"\'"
        where+=" and date(date_order)<=\'"+str(self.date_to)+"\'"
        where+=" and state='sale'"
        if self.customers:
            if len(self.customers)>1:
                where += " and partner_id in " + str(tuple(self.customers.ids))
            else:
                where += " and partner_id = " + str(self.customers.ids[0])

        if self.sales_orders:
            if len(self.sales_orders)>1:
                where += " and id in " + str(tuple(self.sales_orders.ids))
            else:
                where += " and id = " + str(self.sales_orders.ids[0])
        query = """
            select  partner_id,sum(amount_total) as amount 
            from sale_order 
            where {where}
            group by partner_id order by amount desc
            limit {no_of_customers}
            """.format(no_of_customers=self.no_of_customers,where=where)
        self._cr.execute(query)
        lines = self._cr.dictfetchall()
        return lines


    def preview(self):
        self.lines = [(5, 0, 0)]
        line_list=[]
        lines=self._get_lines()
        for line in lines:
            line_list.append((0,0,{
                'customer':line.get('partner_id'),
                'amount':line.get('amount')
            }))
        self.lines=line_list
        return {
            'type': 'ir.actions.act_window',
            'res_model': "odoo_mo.top_customers",
            'res_id': self.id,
            'view_mode': 'form,tree',
            'name': 'Top Customers',
            'target': 'new'
        }

    def dynamic_view(self):
        lines = self._get_lines()
        for line in lines:
            line['partner_name']=self.env['res.partner'].search([('id','=',line.get('partner_id'))],limit=1).name
        return {
            'name': "Top Customers",
            'type': 'ir.actions.client',
            'tag': 'top_customers_view',
            'lines': lines,
        }

    def print_pdf(self):
        data={}
        lines = self._get_lines()
        data['lines']=lines
        return self.env.ref('odoo_mo_top_customers.odoo_mo_top_customers_action').report_action([], data=data)

    def print_excel(self):
        data = {}
        lines = self._get_lines()
        data['lines'] = lines
        return self.env.ref('odoo_mo_top_customers.odoo_mo_top_customers_action_xlsx').report_action([],data=data)


class Template(models.TransientModel):
    _name = 'odoo_mo.top_customers_template'

    customer = fields.Many2one(comodel_name="res.partner", string="Customer", readonly=True)

    amount = fields.Float(string="Amount", readonly=True)

    wiz_id = fields.Many2one(comodel_name="odoo_mo.top_customers")
