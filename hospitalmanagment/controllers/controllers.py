# -*- coding: utf-8 -*-
from odoo import http

# class Hospitalmanagment(http.Controller):
#     @http.route('/hospitalmanagment/hospitalmanagment/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hospitalmanagment/hospitalmanagment/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hospitalmanagment.listing', {
#             'root': '/hospitalmanagment/hospitalmanagment',
#             'objects': http.request.env['hospitalmanagment.hospitalmanagment'].search([]),
#         })

#     @http.route('/hospitalmanagment/hospitalmanagment/objects/<model("hospitalmanagment.hospitalmanagment"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hospitalmanagment.object', {
#             'object': obj
#         })