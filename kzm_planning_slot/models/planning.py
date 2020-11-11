# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PlanningSlotTemplate(models.Model):
    _inherit = 'planning.slot.template'

    line_ids = fields.One2many('planning.slot.line', 'slot_id', 'Lines')

    def do_generate(self):
        line_obj = self.env['planning.slot.line']
        print("okokokokokkokoko")
        for rec in self:
            print("vfvfvfvfvfv")
            rec.line_ids.unlink()
            ds = rec.start_time
            duration = rec.duration

            print("ds    :",ds)
            print("duration    :",duration)
            while ds < rec.start_time + duration:
                line_obj.create({
                    'start_time': ds%24,
                    'duration': 1,
                    'slot_id': rec.id,
                })
                ds = ds + 1
        return True


class PlanningSlotLine(models.Model):
    _name = 'planning.slot.line'
    _description = 'Planning Slot Line'
    _rec_name = 'start_time'

    slot_id = fields.Many2one('planning.slot.template', string="Planning Slot")
    start_time = fields.Float('Start hour', default=0)
    duration = fields.Float('Duration (hours)', default=0)

    def name_get(self):
        res = []
        for rec in self:
            name = "{:02d}h".format(int(rec.start_time))
            res.append((rec.id, name))
        return res