# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

import json

from odoo import http, fields
from odoo.http import request

from ..models.formio_builder import \
    STATE_CURRENT as BUILDER_STATE_CURRENT

from ..models.formio_form import \
    STATE_PENDING as FORM_STATE_PENDING, STATE_DRAFT as FORM_STATE_DRAFT, \
    STATE_COMPLETE as FORM_STATE_COMPLETE, STATE_CANCEL as FORM_STATE_CANCEL


class FormioPublicController(http.Controller):

    ###############
    # Form - public
    ###############

    @http.route('/formio/public/form/<string:uuid>', type='http', auth='public', website=True)
    def public_form_root(self, uuid, **kwargs):
        form = self._get_public_form(uuid, self._check_public_form())
        if not form:
            msg = 'Form UUID %s' % uuid
            return request.not_found(msg)

        ## TODO languages ##
        ## Determine lang.iso from request.__dict__

        # Needed to update language
        # context = request.env.context.copy()
        # context.update({'lang': request.env.user.lang})
        # request.env.context = context

        # # Get active languages used in Builder translations.
        # query = """
        #     SELECT
        #       DISTINCT(fbt.lang_id) AS lang_id
        #     FROM
        #       formio_builder_translation AS fbt
        #       INNER JOIN res_lang AS l ON l.id = fbt.lang_id
        #     WHERE
        #       fbt.builder_id = {builder_id}
        #       AND l.active = True
        # """.format(builder_id=form.builder_id.id)

        # request.env.cr.execute(query)
        # builder_lang_ids = [r[0] for r in request.env.cr.fetchall()]

        # # Always include english (en_US).
        # domain = ['|', ('id', 'in', builder_lang_ids), ('code', 'in', [request.env.user.lang, 'en_US'])]
        # languages = request.env['res.lang'].with_context(active_test=False).search(domain, order='name asc')
        # languages = languages.filtered(lambda r: r.id in builder_lang_ids or r.code == 'en_US')

        values = {
            'languages': [], # initialize, otherwise template/view crashes.
            'form': form,
            'formio_css_assets': form.builder_id.formio_css_assets,
            'formio_js_assets': form.builder_id.formio_js_assets,
        }
        # if len(languages) > 1:
        #     values['languages'] = languages
        return request.render('formio.formio_form_public_embed', values)

    @http.route('/formio/public/form/<string:form_uuid>/config', type='json', auth='public', website=True)
    def form_config(self, form_uuid, **kwargs):
        form = self._get_public_form(form_uuid, self._check_public_form())
        res = {'schema': {}, 'options': {}, 'config': {}}

        if form and form.builder_id.schema:
            res['schema'] = json.loads(form.builder_id.schema)
            res['options'] = self._prepare_form_options(form)

        return res

    @http.route('/formio/public/form/<string:uuid>/submission', type='json', auth='public', website=True)
    def public_form_submission(self, uuid, **kwargs):
        form = self._get_public_form(uuid, self._check_public_form())

        # Submission data
        if form and form.submission_data:
            submission_data = json.loads(form.submission_data)
        else:
            submission_data = {}

        # ETL Odoo data
        if form:
            etl_odoo_data = form.sudo()._etl_odoo_data()
            submission_data.update(etl_odoo_data)

        return json.dumps(submission_data)

    @http.route('/formio/public/form/<string:uuid>/submit', type='json', auth="public", methods=['POST'], website=True)
    def public_form_submit(self, uuid, **post):
        """ POST with ID instead of uuid, to get the model object right away """

        form = self._get_public_form(uuid, self._check_public_form())
        if not form:
            # TODO raise or set exception (in JSON resonse) ?
            return

        vals = {
            'submission_data': json.dumps(post['data']),
            'submission_user_id': request.env.user.id,
            'submission_date': fields.Datetime.now(),
        }

        if post['data'].get('saveDraft') and not post['data'].get('submit'):
            vals['state'] = FORM_STATE_DRAFT
        else:
            vals['state'] = FORM_STATE_COMPLETE

        form.write(vals)

    ######################
    # Form - public create
    ######################

    @http.route('/formio/public/form/create/<string:builder_uuid>', type='http', auth='public', methods=['GET'], website=True)
    def public_form_create_root(self, builder_uuid, **kwargs):
        formio_builder = self._get_public_builder(builder_uuid)

        if not formio_builder:
            msg = 'Form Builder UUID %s: not found' % builder_uuid
            return request.not_found(msg)
        elif not formio_builder.public:
            msg = 'Form Builder UUID %s: not public' % builder_uuid
            return request.not_found(msg)
        # elif not formio_builder.state != BUILDER_STATE_CURRENT:
        #     msg = 'Form Builder UUID %s not current/published' % builder_uuid
        #     return request.not_found(msg)

        ## TODO languages ##
        ## Determine lang.iso from request.__dict__

        # Needed to update language
        # context = request.env.context.copy()
        # context.update({'lang': request.env.user.lang})
        # request.env.context = context

        # # Get active languages used in Builder translations.
        # query = """
        #     SELECT
        #       DISTINCT(fbt.lang_id) AS lang_id
        #     FROM
        #       formio_builder_translation AS fbt
        #       INNER JOIN res_lang AS l ON l.id = fbt.lang_id
        #     WHERE
        #       fbt.builder_uuid = {builder_uuid}
        #       AND l.active = True
        # """.format(builder_uuid=form.builder_uuid.id)

        # request.env.cr.execute(query)
        # builder_lang_ids = [r[0] for r in request.env.cr.fetchall()]

        # # Always include english (en_US).
        # domain = ['|', ('id', 'in', builder_lang_ids), ('code', 'in', [request.env.user.lang, 'en_US'])]
        # languages = request.env['res.lang'].with_context(active_test=False).search(domain, order='name asc')
        # languages = languages.filtered(lambda r: r.id in builder_lang_ids or r.code == 'en_US')

        values = {
            'languages': [], # initialize, otherwise template/view crashes.
            'builder': formio_builder,
            'public_form_create': True,
            'formio_builder_uuid': formio_builder.uuid,
            'formio_css_assets': formio_builder.formio_css_assets,
            'formio_js_assets': formio_builder.formio_js_assets,
        }
        # if len(languages) > 1:
        #     values['languages'] = languages
        
        return request.render('formio.formio_form_public_create_embed', values)


    @http.route('/formio/public/form/create/<string:builder_uuid>/config', type='json', auth='none', website=True)
    def public_form_create_config(self, builder_uuid, **kwargs):
        formio_builder = self._get_public_builder(builder_uuid)
        res = {'schema': {}, 'options': {}}

        if not formio_builder or not formio_builder.public or formio_builder.state != BUILDER_STATE_CURRENT:
            return res

        if formio_builder.schema:
            res['schema'] = json.loads(formio_builder.schema)
            #res['options'] = self._prepare_form_options(form)
            res['options'] = {'public_create': True, 'embedded': True}
            res['config'] = self._prepare_form_config(formio_builder)

        return res

    @http.route('/formio/public/form/create/<string:builder_uuid>/submit', type='json', auth="none", methods=['POST'], website=True)
    def public_form_create_submit(self, builder_uuid, **post):
        formio_builder = self._get_public_builder(builder_uuid)
        if not formio_builder:
            # TODO raise or set exception (in JSON resonse) ?
            return

        Form = request.env['formio.form']
        vals = {
            'builder_id': formio_builder.id,
            'title': formio_builder.title,
            'public_create': True,
            'submission_data': json.dumps(post['data']),
            'submission_user_id': request.env.ref('base.public_user').id,
            'submission_date': fields.Datetime.now(),
        }

        if post['data'].get('saveDraft') and not post['data'].get('submit'):
            vals['state'] = FORM_STATE_DRAFT
        else:
            vals['state'] = FORM_STATE_COMPLETE

        context = {'tracking_disable': True}

        if not request.env.user:
            public_user = request.env.ref('base.public_user').sudo()
            context['force_company'] = public_user.sudo().company_id.id

        form_model = Form.with_context(**context)
        res = form_model.sudo().create(vals)
        return {'form_uuid': res.uuid}

    def _prepare_form_options(self, form):
        options = {}
        context = request.env.context
        Lang  = request.env['res.lang']

        if form.state in [FORM_STATE_COMPLETE, FORM_STATE_CANCEL]:
            options['readOnly'] = True

            if form.builder_id.view_as_html:
                options['renderMode'] = 'html'
                options['viewAsHtml'] = True # backwards compatible (version < 4.x)?

        lang = Lang._lang_get(request.env.user.lang)
        if lang:
            options['language'] = lang.iso_code[:2]
            options['i18n'] = form.i18n_translations()
        return options

    def _prepare_form_config(self, builder):
        config = {
            'public_submit_done_url': builder.public_submit_done_url
        }
        return config

    def _get_public_form(self, form_uuid, public_share=False):
        return request.env['formio.form'].get_public_form(form_uuid, public_share)

    def _get_public_builder(self, builder_uuid):
        return request.env['formio.builder'].get_public_builder(builder_uuid)

    def _check_public_form(self):
        return request._uid == request.env.ref('base.public_user').id or request._uid
