# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Wizard(models.TransientModel):
    _name = 'odoo_mo.odoo_mo_top_selling_products'

    date_from = fields.Date(string="Date From",required=True)
    date_to = fields.Date(string="Date From",required=True)
    sales_orders = fields.Many2many(comodel_name="sale.order", relation="top_selling_sales",
                                        string="Sales Orders")
    products = fields.Many2many(comodel_name="product.product", relation="top_product_products", string="Products")
    no_of_products = fields.Integer(string="Number Of Products", required=True, default=1)
    lines = fields.One2many(comodel_name="odoo_mo.top_selling_products_template", inverse_name="wiz_id", string="Data",
                            readonly=True)

    def _get_lines(self):
        where="date(sale_order.date_order)>=\'"+str(self.date_from)+"\'"
        where+=" and date(sale_order.date_order)<=\'"+str(self.date_to)+"\'"
        where+=" and sale_order.state='sale'"
        if self.products:
            if len(self.products)>1:
                where += " and sale_order_line.product_id in " + str(tuple(self.products.ids))
            else:
                where += " and sale_order_line.product_id = " + str(self.products.ids[0])

        if self.sales_orders:
            if len(self.sales_orders)>1:
                where += " and order_id in " + str(tuple(self.sales_orders.ids))
            else:
                where += " and order_id = " + str(self.sales_orders.ids[0])
        query = """
            select sale_order_line.product_id,sum(sale_order.amount_total) as amount 
            from sale_order_line 
            join sale_order on sale_order.id=sale_order_line.order_id
            where {where}
            group by sale_order_line.product_id order by amount desc
            limit {no_of_products}
            """.format(no_of_products=self.no_of_products,where=where)
        self._cr.execute(query)
        lines = self._cr.dictfetchall()
        return lines


    def preview(self):
        self.lines = [(5, 0, 0)]
        line_list=[]
        lines=self._get_lines()
        for line in lines:
            line_list.append((0,0,{
                'product':line.get('product_id'),
                'amount':line.get('amount')
            }))
        self.lines=line_list
        return {
            'type': 'ir.actions.act_window',
            'res_model': "odoo_mo.odoo_mo_top_selling_products",
            'res_id': self.id,
            'view_mode': 'form,tree',
            'name': 'Top Selling Product',
            'target': 'new'
        }

    def dynamic_view(self):
        lines = self._get_lines()
        for line in lines:
            line['product_name']=self.env['product.product'].search([('id','=',line.get('product_id'))],limit=1).name
        return {
            'name': "Top Selling Product",
            'type': 'ir.actions.client',
            'tag': 'top_selling_products_view',
            'lines': lines,
        }

    def print_pdf(self):
        data={}
        lines = self._get_lines()
        data['lines']=lines
        return self.env.ref('odoo_mo_top_selling_products.odoo_mo_top_selling_products_action').report_action([], data=data)

    def print_excel(self):
        data = {}
        lines = self._get_lines()
        data['lines'] = lines
        return self.env.ref('odoo_mo_top_selling_products.odoo_mo_top_selling_products_action_xlsx').report_action([],data=data)


class Template(models.TransientModel):
    _name = 'odoo_mo.top_selling_products_template'

    product = fields.Many2one(comodel_name="product.product", string="Product", readonly=True)

    amount = fields.Float(string="Amount", readonly=True)

    wiz_id = fields.Many2one(comodel_name="odoo_mo.odoo_mo_top_selling_products")
