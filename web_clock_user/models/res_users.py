from odoo import api, fields, models


class Partner(models.Model):
	_inherit = "res.partner"

	show_clock = fields.Boolean("Show clock", default=True)
	show_clock_type = fields.Selection([('quartz', 'Quartz'), ('mechanical', 'Mechanical')], 'Movement', default="quartz")


class Users(models.Model):
	_inherit = "res.users"
	
	# User can write on a few of his own fields (but not his groups for example)
	SELF_WRITEABLE_FIELDS = ['signature', 'action_id', 'company_id', 'email', 'name', 'image_1920', 'lang', 'tz', 'show_clock', 'show_clock_type']
	# User can read a few of his own fields
	SELF_READABLE_FIELDS = ['signature', 'company_id', 'login', 'email', 'name', 'image_1920', 'image_1024', 'image_512', 'image_256', 'image_128', 'lang', 'tz', 'tz_offset', 'groups_id', 'partner_id', '__last_update', 'action_id', 'show_clock', 'show_clock_type']

	show_clock = fields.Boolean(related='partner_id.show_clock', inherited=True)
	show_clock_type = fields.Selection(related='partner_id.show_clock_type', inherited=True)

