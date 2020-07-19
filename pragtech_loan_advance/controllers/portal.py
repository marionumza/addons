# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class PortalAccountLoan(CustomerPortal):
    

    def _prepare_portal_layout_values(self):
        print ("Count ======== >>>>>>>>>>>>>>>>  LOAN")
        values = super(PortalAccountLoan, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        AccountLoan = request.env['account.loan']
        loan_count = AccountLoan.search_count([
        ])

        values.update({
            'loan_count': loan_count,
        })
        return values
    # ------------------------------------------------------------
    # My Loans
    # ------------------------------------------------------------
 
    def _loan_get_page_view_values(self, loan, access_token, **kwargs):
        values = {
            'page_name': 'loan',
            'loan': loan,
        }
        return self._get_page_view_values(loan, access_token, values, 'my_loan_history', False, **kwargs)
# 
    @http.route(['/my/loans', '/my/loans/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_loan(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        AccountLoan = request.env['account.loan']
# 
        domain = []
# 
        searchbar_sortings = {
            'date': {'label': _('Apply Date'), 'order': 'apply_date desc'},
#             'duedate': {'label': _('Due Date'), 'order': 'date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
#             'state': {'label': _('Status'), 'order': 'state'},
        }
#         # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
# 
        archive_groups = self._get_archive_groups('account.loan', domain)
#         if date_begin and date_end:
#             domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
# 
#         # count for pager
        loan_count = AccountLoan.search_count(domain)
#         # pager
        pager = portal_pager(
            url="/my/loans",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=loan_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        loans = AccountLoan.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_loan_history'] = loans.ids[:100]
        print ("Loadnnnnnn  ",loans)
        values.update({
            'date': date_begin,
            'loans': loans,
            'page_name': 'loan',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/loans',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("pragtech_loan_advance.portal_my_loans", values)
    
    
    @http.route(['/my/loans/<int:loan_id>'], type='http', auth="public", website=True)
    def portal_my_loan_detail(self, loan_id, access_token=None, report_type=None, download=False, **kw):
        try:
            invoice_sudo = self._document_check_access('account.loan', loan_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
 
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=invoice_sudo, report_type=report_type, report_ref='account.account_invoices', download=download)
 
        values = self._loan_get_page_view_values(invoice_sudo, access_token, **kw)
        return request.render("account.portal_invoice_page", values)
    
#     
#     @http.route(['/my/loan/<int:loan_id>/',
#                  '/my/loan/<int:loan_id>/<string:uuid>'], type='http', auth="public", website=True)
#     def membership(self, account_id, uuid='', message='', message_class='', **kw):
#         values = {}
#         if account_id:
#             membership_line = request.env['membership.membership_line'].sudo().search([('id', '=', account_id)])
#             print("\n\n in controller method  of member ship ", uuid, account_id, membership_line)
# 
#         values.update({
#             'partner':membership_line.partner,
#             'membership_line':membership_line
# 
#         })

        return request.render('doyenne_theme.portal_membership_page', values)
 
