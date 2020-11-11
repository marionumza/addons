# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    workcenter_id = fields.Many2one('mrp.workcenter', 'Workcenter')

    # @api.model
    # def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
    #     if self._context.get('nw_workcenter_id'):
    #         nw_workcenter_id = self.env['mrp.workcenter'].browse(self._context.get('nw_workcenter_id'))
    #         if nw_workcenter_id:
    #             args.append(('id', 'in', nw_workcenter_id.employee_ids.ids))
    #     return super(HrEmployee, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
