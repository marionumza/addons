# -*- coding: utf-8 -*-

import pytz
import datetime

from odoo.addons.turno_online.helpers import functions

from odoo import http, modules, tools
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class OnlineTurno(http.Controller):

    def ld_to_utc(self, ld, appointee_id, duration=False):

        date_parsed = datetime.datetime.strptime(ld, "%Y-%m-%d  %H:%M")
        if duration:
            date_parsed += datetime.timedelta(hours=duration)

        user = request.env['res.users'].sudo().search([('id', '=', appointee_id)])
        if user:
            if user.tz:
                tz = user.tz
            else:
                tz = 'America/Argentina/Buenos_Aires'
            local = pytz.timezone(tz)
            local_dt = local.localize(date_parsed, is_dst=None)
            return local_dt.astimezone(pytz.utc)
        else:
            return ld

    def appointee_id_to_partner_id(self, appointee_id):

        appointee = request.env['res.users'].sudo().search([('id', '=', appointee_id)])
        if appointee:
            return appointee.partner_id.id
        else:
            return False

    def select_appointees(self, criteria='default'):

        schedules = request.env['pronexo.turno.schedule'].sudo().search([])
        appointee_ids = [s.user_id.id for s in schedules]
        appointee_ids = list(set(appointee_ids))
        return appointee_ids

    def select_options(self, criteria='default'):

        return request.env['pronexo.turno.option'].sudo().search([])

    def prepare_values(self, form_data=False, default_appointee_id=False, criteria='default'):

        appointee_ids = self.select_appointees(criteria=criteria)
        options = self.select_options(criteria=criteria)

        values = {
            'appointees': request.env['res.users'].sudo().search([('id', 'in', appointee_ids)]),
            'turno_options': options,
            'timeschedules': [],
            'appointee_id': 0,
            'turno_option_id': 0,
            'turno_date': '',
            'timeschedule_id': 0,
            'mode': 'public' if request.env.user._is_public() else 'registered',
            'name': request.env.user.partner_id.name if not request.env.user._is_public() else '',
            'email': request.env.user.partner_id.email if not request.env.user._is_public() else '',
            'phone': request.env.user.partner_id.phone if not request.env.user._is_public() else '',
            'mobile': request.env.user.partner_id.mobile if not request.env.user._is_public() else '',
            'remarks': '',
            'error': {},
            'error_message': [],
            'form_action': '/turno-online/turno-confirm',
            'form_criteria': criteria
        }

        if form_data:
            try:
                appointee_id = int(form_data.get('appointee_id', 0))
            except:
                appointee_id = 0

            try:
                turno_option_id = int(form_data.get('turno_option_id', 0))
            except:
                turno_option_id = 0

            try:
                timeschedule_id = int(form_data.get('timeschedule_id', 0))
            except:
                timeschedule_id = 0

            try:
                turno_date = datetime.datetime.strptime(form_data['turno_date'], '%d/%m/%Y').strftime('%d/%m/%Y')
            except:
                turno_date = ''

            values.update({
                'name': form_data.get('name', ''),
                'email': form_data.get('email', ''),
                'phone': form_data.get('phone', ''),
                'mobile': form_data.get('mobile', ''),
                'appointee_id': appointee_id,
                'turno_option_id': turno_option_id,
                'turno_date': turno_date,
                'timeschedule_id': timeschedule_id,
                'remarks': form_data.get('remarks', '')
            })

            if appointee_id and turno_option_id and turno_date:
                free_schedules = self.get_free_turno_schedules_for_day(turno_option_id, form_data['turno_date'], appointee_id, criteria)
                days_with_free_schedules = self.get_days_with_free_schedules(turno_option_id,
                                                                     appointee_id,
                                                                     datetime.datetime.strptime(form_data['turno_date'], '%d/%m/%Y').year,
                                                                     datetime.datetime.strptime(form_data['turno_date'], '%d/%m/%Y').month,
                                                                     criteria)
                values.update({
                    'timeschedules': free_schedules,
                    'days_with_free_schedules': days_with_free_schedules,
                    'focus_year': datetime.datetime.strptime(form_data['turno_date'], '%d/%m/%Y').year,
                    'focus_month': datetime.datetime.strptime(form_data['turno_date'], '%d/%m/%Y').month
                })
        else:
            if values['appointees']:
                try:
                    default_appointee_id = int(default_appointee_id)
                except:
                    default_appointee_id = False
                if default_appointee_id and default_appointee_id in values['appointees'].ids:
                    values['appointee_id'] = default_appointee_id
                else:
                    values['appointee_id'] = values['appointees'][0].id
            if options:
                values['turno_option_id'] = options[0].id
        return values

    @http.route(['/turno-online'], auth='public', website=True, csrf=True)
    def online_turno(self, **kw):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'turno_online')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('turno_online.only_registered_users')
        values = self.prepare_values(default_appointee_id=kw.get('appointee', False))

        return request.render('turno_online.make_turno', values)

    @http.route(['/turno-online/turno-confirm'], auth="public", type='http', website=True)
    def online_turno_confirm(self, **post):
        error = {}
        error_message = []

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'turno_online')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('turno_online.only_registered_users')

            if not post.get('name', False):
                error['name'] = True
                error_message.append(_('Please enter your name.'))
            if not post.get('email', False):
                error['email'] = True
                error_message.append(_('Please enter your email address.'))
            elif not functions.valid_email(post.get('email', '')):
                error['email'] = True
                error_message.append(_('Please enter a valid email address.'))
            if not post.get('phone', False):
                error['phone'] = True
                error_message.append(_('Please enter your phonenumber.'))
            if not post.get('mobile', False):
                error['mobile'] = True
                error_message.append(_('Please enter your mobilenumber.'))

        try:
            appointee_id = int(post.get('appointee_id', 0))
        except:
            appointee_id = 0
        if not appointee_id:
            error['appointee_id'] = True
            error_message.append(_('Please select a valid appointee.'))

        option = request.env['pronexo.turno.option'].sudo().search([('id', '=', int(post.get('turno_option_id', 0)))])
        if not option:
            error['turno_option_id'] = True
            error_message.append(_('Please select a valid subject.'))

        schedule = request.env['pronexo.turno.schedule'].sudo().search([('id', '=', int(post.get('timeschedule_id', 0)))])
        if not schedule:
            error['timeschedule_id'] = True
            error_message.append(_('Please select a valid timeschedule.'))

        try:
            date_start = datetime.datetime.strptime(post['turno_date'], '%d/%m/%Y').strftime('%Y-%m-%d')
            day_schedule = date_start + ' ' + functions.float_to_time(schedule.schedule)
            start_datetime = self.ld_to_utc(day_schedule, appointee_id)
        except:
            error['turno_date'] = True
            error_message.append(_('Please select a valid date.'))

        values = self.prepare_values(form_data=post)
        if error_message:
            values['error'] = error
            values['error_message'] = error_message
            return request.render('turno_online.make_turno', values)

        if not self.check_schedule_is_possible(option.id, post['turno_date'], appointee_id, schedule.id):
            values['error'] = {'timeschedule_id': True}
            values['error_message'] = [_('schedule is already occupied, please choose another schedule.')]
            return request.render('turno_online.make_turno', values)

        if request.env.user._is_public():
            partner = request.env['res.partner'].sudo().search(['|', ('phone', 'ilike', values['phone']),
                                                                     ('mobile', 'ilike', values['mobile']),   
                                                                     ('email', 'ilike', values['email'])])
            if partner:
                partner_ids = [self.appointee_id_to_partner_id(appointee_id),
                               partner[0].id]
            else:
                partner = request.env['res.partner'].sudo().create({
                    'name': values['name'],
                    'phone': values['phone'],
                    'mobile': values['mobile'],
                    'email': values['email']
                })
                partner_ids = [self.appointee_id_to_partner_id(appointee_id),
                               partner[0].id]
        else:
            partner_ids = [self.appointee_id_to_partner_id(appointee_id),
                           request.env.user.partner_id.id]

        # set detaching = True, we do not want to send a mail to the attendees
        turno = request.env['calendar.event'].sudo().with_context(detaching=True).create({
            'name': option.name,
            'description': post.get('remarks', ''),
            'start': start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'stop': (start_datetime + datetime.timedelta(minutes=round(option.duration * 60))).strftime("%Y-%m-%d %H:%M:%S"),
            'duration': option.duration,
            'partner_ids': [(6, 0, partner_ids)]
        })
        # set all attendees on 'accepted'
        turno.attendee_ids.write({
            'state': 'accepted'
        })

        # registered user, we want something to show in his portal
        if not request.env.user._is_public():
            vals = {
                'partner_id': request.env.user.partner_id.id,
                'appointee_id': self.appointee_id_to_partner_id(appointee_id),
                'event_id': turno.id
            }
            registration = request.env['pronexo.turno.registration'].create(vals)

        return request.redirect('/turno-online/turno-scheduled?turno=%d' % turno.id)

    @http.route(['/turno-online/turno-scheduled'], auth="public", type='http', website=True)
    def confirmed(self, **post):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'turno_online')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('turno_online.only_registered_users')

        turno = request.env['calendar.event'].sudo().search([('id', '=', int(post.get('turno', 0)))])
        if not turno:
            values = {
                'turno': False,
                'error_message': [_('turno not found.')]
            }
            return request.render('turno_online.thanks', values)

        if request.env.user._is_public():
            values = {
                'turno': False,
                'error_message': []
            }
            return request.render('turno_online.thanks', values)
        else:
            if request.env.user.partner_id.id not in turno.partner_ids.ids:
                values = {
                    'turno': False,
                    'error_message': [_('turno not found.')]
                }
                return request.render('turno_online.thanks', values)

            values = {
                'turno': turno,
                'error_message': []
            }
            return request.render('turno_online.thanks', values)

    def recurrent_events_overlapping(self, appointee_id, event_start, event_stop):
        query = """
                    SELECT e.id FROM calendar_event e, calendar_event_res_partner_rel ep  
                        WHERE ep.res_partner_id = %s AND
                              e.active = true AND
                              e.recurrency = true AND
                              e.final_date >= %s AND
                              e.id = ep.calendar_event_id                                         
        """
        request.env.cr.execute(query, (self.appointee_id_to_partner_id(appointee_id),
                                       datetime.datetime.now().strftime('%Y-%m-%d')))
        res = request.env.cr.fetchall()
        event_ids = [r[0] for r in res]
        for event in request.env['calendar.event'].sudo().browse(event_ids):
            recurrent_dates = event._get_recurrent_dates_by_event()
            for recurrent_start_date, recurrent_stop_date in recurrent_dates:
                recurrent_start_date_short = recurrent_start_date.strftime('%Y-%m-%d %H:%M')
                recurrent_stop_date_short = recurrent_stop_date.strftime('%Y-%m-%d %H:%M')
                if (event_start <= recurrent_start_date_short <= event_stop) or (
                        recurrent_start_date_short <= event_start and recurrent_stop_date_short >= event_stop) or (
                        event_start <= recurrent_stop_date_short <= event_stop):
                    return True
        return False

    def check_schedule_is_possible(self, option_id, turno_date, appointee_id, schedule_id):

        if not turno_date:
            return False

        if not appointee_id:
            return False

        if not option_id:
            return False

        if not schedule_id:
            return False

        option = request.env['pronexo.turno.option'].sudo().search([('id', '=', option_id)])
        if not option:
            return False
        schedule = request.env['pronexo.turno.schedule'].sudo().search([('id', '=', schedule_id)])
        if not schedule:
            return False

        date_start = datetime.datetime.strptime(turno_date, '%d/%m/%Y').strftime('%Y-%m-%d')

        # if today, then skip schedules in te past (< current time)
        if date_start == datetime.datetime.now().strftime('%Y-%m-%d') and self.ld_to_utc(date_start + ' ' + functions.float_to_time(schedule.schedule), appointee_id) < datetime.datetime.now(pytz.utc):
            return False

        event_start = self.ld_to_utc(date_start + ' ' + functions.float_to_time(schedule.schedule), appointee_id).strftime("%Y-%m-%d %H:%M:%S")
        event_stop = self.ld_to_utc(date_start + ' ' + functions.float_to_time(schedule.schedule), appointee_id,
                                    duration=option.duration).strftime("%Y-%m-%d %H:%M:%S")

        query = """
                SELECT e.id FROM calendar_event e, calendar_event_res_partner_rel ep  
                    WHERE ep.res_partner_id = %s AND
                          e.active = true AND
                          (e.recurrency = false or e.recurrency is null) AND
                          e.id = ep.calendar_event_id AND 
                        ((e.start >= %s AND e.start <= %s) OR
                             (e.start <= %s AND e.stop >= %s) OR
                             (e.stop >= %s) AND e.stop <= %s)                                       
        """
        request.env.cr.execute(query, (self.appointee_id_to_partner_id(appointee_id),
                                       event_start, event_stop,
                                       event_start, event_stop,
                                       event_start, event_stop))
        res = request.env.cr.fetchall()
        if not res:
            if not self.recurrent_events_overlapping(appointee_id, event_start, event_stop):
                return True

        return False

    def filter_schedules(self, schedules, criteria):
        # override this method when schedules needs to be filtered
        return schedules

    def get_free_turno_schedules_for_day(self, option_id, turno_date, appointee_id, criteria):

        def schedule_present(schedules, schedule):

            for s in schedules:
                if s['timeschedule'] == functions.float_to_time(schedule):
                    return True
            return False

        if not turno_date:
            return []

        if not appointee_id:
            return []

        option = request.env['pronexo.turno.option'].sudo().search([('id', '=', option_id)])
        if not option:
            return []

        week_day = datetime.datetime.strptime(turno_date, '%d/%m/%Y').weekday()
        schedules = request.env['pronexo.turno.schedule'].sudo().search([('user_id', '=', appointee_id),
                                                                   ('day', '=', str(week_day))])
        schedules = self.filter_schedules(schedules, criteria)

        date_start = datetime.datetime.strptime(turno_date, '%d/%m/%Y').strftime('%Y-%m-%d')
        free_schedules = []
        for schedule in schedules:
            # skip double schedules
            if schedule_present(free_schedules, schedule.schedule):
                continue

            # if today, then skip schedules in te past (< current time)
            if date_start == datetime.datetime.now().strftime('%Y-%m-%d') and self.ld_to_utc(date_start + ' ' + functions.float_to_time(schedule.schedule), appointee_id) < datetime.datetime.now(pytz.utc):
                continue

            event_start = self.ld_to_utc(date_start + ' ' + functions.float_to_time(schedule.schedule), appointee_id).strftime("%Y-%m-%d %H:%M:%S")
            event_stop = self.ld_to_utc(date_start + ' ' + functions.float_to_time(schedule.schedule), appointee_id,
                                        duration=option.duration).strftime("%Y-%m-%d %H:%M:%S")

            # check normal calendar events
            query = """
                    SELECT e.id FROM calendar_event e, calendar_event_res_partner_rel ep  
                        WHERE ep.res_partner_id = %s AND
                              e.active = true AND
                              (e.recurrency = false or e.recurrency is null) AND 
                              e.id = ep.calendar_event_id AND 
                            ((e.start >= %s AND e.start <= %s) OR
                             (e.start <= %s AND e.stop >= %s) OR
                             (e.stop >= %s) AND e.stop <= %s)                                         
            """
            request.env.cr.execute(query, (self.appointee_id_to_partner_id(appointee_id),
                                           event_start, event_stop,
                                           event_start, event_stop,
                                           event_start, event_stop))
            res = request.env.cr.fetchall()
            if not res:
                if not self.recurrent_events_overlapping(appointee_id, event_start, event_stop):
                    free_schedules.append({
                        'id': schedule.id,
                        'timeschedule': functions.float_to_time(schedule.schedule)
                    })

        return free_schedules

    def get_days_with_free_schedules(self, option_id, appointee_id, year, month, criteria):

        if not option_id:
            return {}

        if not appointee_id:
            return {}

        start_datetimes = {}
        start_date = datetime.date(year, month, 1)
        for i in range(31):
            if start_date < datetime.date.today():
                start_date += datetime.timedelta(days=1)
                continue
            if start_date.weekday() not in start_datetimes:
                start_datetimes[start_date.weekday()] = []
            start_datetimes[start_date.weekday()].append(start_date.strftime('%Y-%m-%d'))
            start_date += datetime.timedelta(days=1)
            if start_date.month != month:
                break

        day_schedules = []

        option = request.env['pronexo.turno.option'].sudo().search([('id', '=', option_id)])
        if not option:
            return {}

        for weekday, dates in start_datetimes.items():
            schedules = request.env['pronexo.turno.schedule'].sudo().search([('user_id', '=', appointee_id),
                                                                       ('day', '=', str(weekday))])
            schedules = self.filter_schedules(schedules, criteria)

            for schedule in schedules:
                for d in dates:
                    # if d == today, then skip schedules in te past (< current time)
                    if d == datetime.datetime.now().strftime('%Y-%m-%d') and self.ld_to_utc(d + ' ' + functions.float_to_time(schedule.schedule), appointee_id) < datetime.datetime.now(pytz.utc):
                        continue

                    day_schedules.append({
                        'timeschedule': functions.float_to_time(schedule.schedule),
                        'date': d,
                        'start': self.ld_to_utc(d + ' ' + functions.float_to_time(schedule.schedule), appointee_id).strftime("%Y-%m-%d %H:%M:%S"),
                        'stop': self.ld_to_utc(d + ' ' + functions.float_to_time(schedule.schedule), appointee_id, duration=option.duration).strftime("%Y-%m-%d %H:%M:%S")
                    })
        days_with_free_schedules = {}
        for d in day_schedules:
            if d['date'] in days_with_free_schedules:
                # this day is possible, there was a schedule possible so skip other schedule calculations for this day
                # We only need to inform the visitor he can click on this day (green), after that he needs to
                # select a valid schedule.
                continue

            query = """
                    SELECT e.id FROM calendar_event e, calendar_event_res_partner_rel ep  
                        WHERE ep.res_partner_id = %s AND 
                              e.active = true AND
                              (e.recurrency = false or e.recurrency is null) AND
                              e.id = ep.calendar_event_id AND  
                            ((e.start >= %s AND e.start <= %s) OR
                             (e.start <= %s AND e.stop >= %s) OR
                             (e.stop >= %s) AND e.stop <= %s)                                         
            """
            request.env.cr.execute(query, (self.appointee_id_to_partner_id(appointee_id),
                                           d['start'], d['stop'],
                                           d['start'], d['stop'],
                                           d['start'], d['stop']))
            res = request.env.cr.fetchall()
            if not res:
                if not self.recurrent_events_overlapping(appointee_id, d['start'], d['stop']):
                    days_with_free_schedules[d['date']] = True
        return days_with_free_schedules

    @http.route('/turno-online/timeschedules', type='json', auth='public', website=True)
    def free_timeschedules(self, turno_option, turno_with, turno_date, form_criteria, **kwargs):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'turno_online')], limit=1)
            if not param or param.value.lower() != 'public':
                return {
                    'timeschedules': [],
                    'days_with_free_schedules': {},
                    'focus_year': 0,
                    'focus_month': 0,
                }

        try:
            option_id = int(turno_option)
        except:
            option_id = 0
        try:
            appointee_id = int(turno_with)
        except:
            appointee_id = 0
        try:
            date_parsed = datetime.datetime.strptime(turno_date, '%d/%m/%Y')
        except:
            date_parsed = datetime.date.today()

        free_schedules = self.get_free_turno_schedules_for_day(option_id, turno_date, appointee_id, form_criteria)
        days_with_free_schedules = self.get_days_with_free_schedules(option_id,
                                                             appointee_id,
                                                             date_parsed.year,
                                                             date_parsed.month,
                                                             form_criteria)
        return {
            'timeschedules': free_schedules,
            'days_with_free_schedules': days_with_free_schedules,
            'focus_year': date_parsed.year,
            'focus_month': date_parsed.month,
        }

    @http.route('/turno-online/month-bookable', type='json', auth='public', website=True)
    def month_bookable(self, turno_option, turno_with, turno_year, turno_month, form_criteria, **kwargs):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'turno_online')], limit=1)
            if not param or param.value.lower() != 'public':
                return {
                    'days_with_free_schedules': [],
                    'focus_year': 0,
                    'focus_month': 0,
                }

        try:
            option_id = int(turno_option)
        except:
            option_id = 0
        try:
            appointee_id = int(turno_with)
        except:
            appointee_id = 0
        try:
            turno_year = int(turno_year)
            turno_month = int(turno_month)
        except:
            turno_year = 0
            turno_month = 0

        if not turno_year or not turno_month:
            turno_year = datetime.date.today().year
            turno_month = datetime.date.today().month

        days_with_free_schedules = self.get_days_with_free_schedules(option_id,
                                                             appointee_id,
                                                             turno_year,
                                                             turno_month,
                                                             form_criteria)

        return {
            'days_with_free_schedules': days_with_free_schedules,
            'focus_year': turno_year,
            'focus_month': turno_month,
        }

    def online_turno_state_change(self, turno, previous_state):
        # method to override when  you want something to happen on state change, for example send mail
        return True

    @http.route(['/turno-online/portal/cancel'], auth="public", type='http', website=True)
    def online_turno_portal_cancel(self, **post):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'turno_online')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('turno_online.only_registered_users')

        try:
            id = int(post.get('turno_to_cancel', 0))
        except:
            id = 0

        if id:
            turno = request.env['pronexo.turno.registration'].search([('id', '=', id)])
            if turno and (
                    turno.partner_id == request.env.user.partner_id or turno.appointee_id == request.env.user.partner_id):
                previous_state = turno.state
                turno.cancel_turno()
                self.online_turno_state_change(turno, previous_state)

        return request.redirect('/my/turnos-online')

    @http.route(['/turno-online/portal/confirm'], auth="public", type='http', website=True)
    def online_turno_portal_confirm(self, **post):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 'turno_online')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('turno_online.only_registered_users')

        try:
            id = int(post.get('turno_to_confirm', 0))
        except:
            id = 0

        if id:
            turno = request.env['pronexo.turno.registration'].search([('id', '=', id)])
            if turno and (
                    turno.partner_id == request.env.user.partner_id or turno.appointee_id == request.env.user.partner_id):
                previous_state = turno.state
                turno.confirm_turno()
                self.online_turno_state_change(turno, previous_state)

        return request.redirect('/my/turnos-online')
