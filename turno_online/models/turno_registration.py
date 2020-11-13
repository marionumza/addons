# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class turnosRegistration(models.Model):
    _name = 'pronexo.turno.registration'
    _description = 'turnos Registration'
    _inherit = ['portal.mixin', 'mail.thread.cc', 'mail.activity.mixin']

    event_id = fields.Many2one('calendar.event', string='Event', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='cascade')
    appointee_id = fields.Many2one('res.partner', string='Appointee', ondelete='cascade')
    turno_begin = fields.Datetime(string="Event Start Date", related='event_id.start', readonly=True, store=True)
    turno_end = fields.Datetime(string="Event End Date", related='event_id.stop', readonly=True)
    name = fields.Char(string='Event', related='event_id.name', readonly=True, store=True)
    state = fields.Selection([
        ('pending', _('Pending')),
        ('valid', _('Scheduled')),
        ('cancel', _('Canceled')),
    ], required=True, default='valid', string='Status', copy=False)
    appointee_interaction = fields.Boolean(string='Appointee interaction', default=False)

    def cancel_turno(self):
        for turno in self:
            if turno.state in ['pending', 'valid']:
                turno.sudo().event_id.write({
                    'active': False
                })
                turno.write({
                    'state': 'cancel'
                })

        return True

    def confirm_turno(self):

        for turno in self:
            if turno.state == 'pending':
                turno.write({
                    'state': 'valid'
                })

        return True
