# -*- coding: utf-8 -*-

from collections import OrderedDict
from operator import itemgetter

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['turno_count'] = request.env['pronexo.turno.registration'].search_count(['|', ('partner_id', '=', request.env.user.partner_id.id),
                                                                                                     '&', ('appointee_id', '=', request.env.user.partner_id.id),
                                                                                                          ('appointee_interaction', '=', True)])
        return values

    # ------------------------------------------------------------
    # Mis turnos
    # ------------------------------------------------------------
    def _turno_get_page_view_values(self, turno, access_token, **kwargs):
        values = {
            'page_name': 'turno',
            'turno': turno,
        }
        return self._get_page_view_values(turno, access_token, values, 'my_turno_history', False, **kwargs)

    @http.route(['/my/turnos-online', '/my/turnos-online/page/<int:page>'], type='http', auth="user", website=True)
    def portal_mis_turnos(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        domain = ['|', ('partner_id', '=', request.env.user.partner_id.id),
                       '&', ('appointee_id', '=', request.env.user.partner_id.id),
                            ('appointee_interaction', '=', True)]

        searchbar_sortings = {
            'new': {'label': _('Newest'), 'order': 'id desc'},
            'date1': {'label': _('Date ↓'), 'order': 'turno_begin'},
            'date2': {'label': _('Date ↑'), 'order': 'turno_begin desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby or sortby not in searchbar_sortings.keys():
            sortby = 'new'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'pending': {'label': _('Pending'), 'domain': [('state', '=', 'pending')]},
            'valid': {'label': _('Confirmed'), 'domain': [('state', '=', 'valid')]},
            'cancel': {'label': _('Canceled'), 'domain': [('state', '=', 'cancel')]},
        }
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters[filterby]['domain'] + domain

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('pronexo.turno.registration', domain)
        if date_begin and date_end:
            domain = [('create_date', '>', date_begin), ('create_date', '<=', date_end)] + domain
        # turno count
        turno_count = request.env['pronexo.turno.registration'].search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/turnos-online",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=turno_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        turnos = request.env['pronexo.turno.registration'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_turno_history'] = turnos.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'turnos': turnos,
            'page_name': 'turno',
            'archive_groups': archive_groups,
            'default_url': '/my/turnos-online',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("turno_online.portal_mis_turnos", values)

    @http.route(['/my/turno-online/<int:turno_id>'], type='http', auth="public", website=True)
    def portal_mi_turno(self, turno_id=None, access_token=None, **kw):
        try:
            turno_sudo = self._document_check_access('pronexo.turno.registration', turno_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._turno_get_page_view_values(turno_sudo, access_token, **kw)
        return request.render("turno_online.portal_mi_turno", values)
