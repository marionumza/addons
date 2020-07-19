from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import formataddr


################
# Mail.Message #
################
class MailMessage(models.Model):
    _name = "mail.message"
    _inherit = "mail.message"

    """
    Check settings and use company's email if forced.
    Make 'From:' look like 'John Smith via Your Company <yorcompany@example.com>
    """
    @api.model
    def _get_default_from(self):

        # Check settings.
        # If not using company email fallback to original function
        user = self.env.user
        company = user.company_id

        if not company.use_company_email:
            if user.email:
                return formataddr((user.name, user.email))
            raise UserError(_("Unable to send email, please configure the sender's email address."))

        if company.email:
            res = self._compose_default_from(company.email)
            if res:
                return res

        raise UserError(_("Unable to send email, please configure company email address."))

    # -- Compose default from
    @api.model
    def _compose_default_from(self, email=False):
        """
        Compose email based on company setting and
        :param email: Char email address
        :return: formatted email (e.g. "Bob Doe via MyCompany <mycompany@example.com>")
        """

        # Check settings.
        # If not using company email fallback to original function
        if not email:
            return False
        user = self.env.user
        company = user.company_id

        if company.add_company_from:
            if company.add_company_mode == 'r':
                name_from = company.name
            else:
                if company.email_joint:
                    name_from = '%s %s %s' % (user.name, company.email_joint, company.name)
                else:
                    name_from = '%s %s' % (user.name, company.name)
        else:
            name_from = user.name

        return formataddr((name_from, email))


###############
# Mail.Thread #
###############
class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_reply_to(self, default=None, records=None, company=None, doc_names=None):
        """
        Cetmix. Based on settings prepend company name with user's name
        This is a copy-paste of the base method. Need to check it regularly for possible changes
        """
        _records = self if self and self._name != 'mail.thread' else records
        model = _records._name if _records and _records._name != 'mail.thread' else False
        res_ids = _records.ids if _records and model else []
        _res_ids = res_ids or [False]  # always have a default value located in False

        alias_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")
        result = dict.fromkeys(_res_ids, False)
        result_email = dict()
        doc_names = doc_names if doc_names else dict()

        if alias_domain:
            if model and res_ids:
                if not doc_names:
                    doc_names = dict((rec.id, rec.display_name) for rec in _records)

                mail_aliases = self.env['mail.alias'].sudo().search([
                    ('alias_parent_model_id.model', '=', model),
                    ('alias_parent_thread_id', 'in', res_ids),
                    ('alias_name', '!=', False)])
                # take only first found alias for each thread_id, to match order (1 found -> limit=1 for each res_id)
                for alias in mail_aliases:
                    result_email.setdefault(alias.alias_parent_thread_id, '%s@%s' % (alias.alias_name, alias_domain))

            # left ids: use catchall
            left_ids = set(_res_ids) - set(result_email)
            if left_ids:
                catchall = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
                if catchall:
                    result_email.update(dict((rid, '%s@%s' % (catchall, alias_domain)) for rid in left_ids))

            # compute name of reply-to - TDE tocheck: quotes and stuff like that
            # Cetmix
            company_id = company if company else self.env.user.company_id

            # Prepend with user's name
            if company_id.add_sender_reply_to:
                if company_id.email_joint:
                    company_name = '%s %s %s' % (self.env.user.name, company_id.email_joint, company_id.name)
                else:
                    company_name = '%s %s' % (self.env.user.name, company_id.name)
            else:
                company_name = company_id.name

            for res_id in result_email.keys():
                name = '%s%s%s' % (company_name, ' ' if doc_names.get(res_id) else '', doc_names.get(res_id, ''))
                result[res_id] = formataddr((name, result_email[res_id]))

        left_ids = set(_res_ids) - set(result_email)
        if left_ids:
            result.update(dict((res_id, default) for res_id in left_ids))

        return result


###############
# Res.Company #
###############
class Company(models.Model):
    _name = "res.company"
    _inherit = "res.company"

    use_company_email = fields.Boolean(string="Use Company Email",
                                       help="Before: From 'Some User <some.user@usermail.com>'\n"
                                            "After: From 'Some User <mycompany@companymail.com>'")
    add_company_from = fields.Boolean(string="Company Name In 'From'",
                                      help="Before: 'Some User <mycompany@example.com>'\n"
                                           "After: Some User via My Company <mycompany@example.com>")
    add_company_mode = fields.Selection(string="Company Name",
                                        selection=[
                                            ('a', 'append to username'),
                                            ('r', 'replace completely')
                                        ], default='a')
    add_sender_reply_to = fields.Boolean(string="Sender's Name In 'Reply-to'",
                                         help="Before: 'My Company <mycompany@example.com>'\n"
                                              "After: Some User via My Company <mycompany@example.com>")
    email_joint = fields.Char(string="Name Joint", translate=True, default='via',
                              help="Before: 'Some User My Company <mycompany@example.com>'\n"
                                   "After: Some User via My Company <mycompany@example.com>")


#################
# Mail Composer #
#################
class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.model
    def default_get(self, fields_list):
        res = super(MailComposer, self).default_get(fields_list)
        res.update({'email_from': self._get_default_from()})
        return res

    @api.model
    def _get_default_from(self):
        """
        Check settings and use company's email if forced.
        Make 'From:' look like 'John Smith via Your Company <yorcompany@example.com>
        """

        # Check settings.
        # If not using company email fallback to original function
        user = self.env.user
        company = user.company_id

        if not company.use_company_email:
            if user.email:
                return formataddr((user.name, user.email))
            raise UserError(_("Unable to send email, please configure the sender's email address."))

        if company.email:
            res = self._compose_default_from(company.email)
            if res:
                return res

        raise UserError(_("Unable to send email, please configure company email address."))


    # -- Compose default from
    @api.model
    def _compose_default_from(self, email=False):
        """
        Compose email based on company setting and
        :param email: Char email address
        :return: formatted email (e.g. "Bob Doe via MyCompany <mycompany@example.com>")
        """

        # Check settings.
        # If not using company email fallback to original function
        if not email:
            return False
        user = self.env.user
        company = user.company_id

        if company.add_company_from:
            if company.add_company_mode == 'r':
                name_from = company.name
            else:
                if company.email_joint:
                    name_from = '%s %s %s' % (user.name, company.email_joint, company.name)
                else:
                    name_from = '%s %s' % (user.name, company.name)
        else:
            name_from = user.name

        return formataddr((name_from, email))
