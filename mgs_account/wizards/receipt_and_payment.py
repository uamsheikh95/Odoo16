from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ReceiptAndPayment(models.TransientModel):
    _name = 'mgs_account.receipt_and_payment'
    _description = 'Receipt and Payment'

    journal_id = fields.Many2one('account.journal', string="Journal")
    partner_id = fields.Many2one('res.partner', string="Partner")
    user_id = fields.Many2one('res.users', string='User')
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    payment_type = fields.Selection([('Receipt', 'Receipt'), ('Payment', 'Payments')],
                                    string='Payment Type', default='Receipt', required=True)

    @api.constrains('date_from', 'date_to')
    def _check_the_date_from_and_to(self):
        if self.date_to and self.date_from and self.date_to < self.date_from:
            raise ValidationError('''From Date should be less than To Date.''')

    def confirm(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'journal_id': [self.journal_id.id, self.journal_id.name],
                'user_id': [self.user_id.id, self.user_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'payment_type': self.payment_type,
            },
        }

        return self.env.ref('mgs_account.action_receipt_and_payment').report_action(self, data=data)


class ReceiptAndPaymentReport(models.AbstractModel):
    _name = 'report.mgs_account.receipt_and_payment_report'
    _description = 'Receipt and Payment Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id, journal_id, user_id, payment_type):
        p_type = 'outbound' if payment_type == 'Receipt' else 'inbound'

        p_type = """('Receivable')""" if payment_type == 'Receipt' else """('Payable')"""

        params = []

        query = """
        select am.name as receipt_no, rp.id as partner_id, rp.name as partner_name, aml.name as ref,
        rp.mobile as phone, aml.date as date, sum(aml.credit-aml.debit) as amount_paid, aj.name as journal_name
        from account_move_line as aml
        left join res_partner as rp on aml.partner_id=rp.id
        left join account_journal as aj on aml.journal_id=aj.id
        left join account_move as am on aml.move_id=am.id
        left join account_account as aa on aml.account_id=aa.id
        left join account_account_type as aat on aa.user_type_id=aat.id
        where aat.name = """ + p_type + """
        and aml.credit > 0 and aj.type in ('bank', 'cash')"""

        if date_from:
            params.append(date_from)
            query += """ and aml.date >= %s"""

        if date_to:
            params.append(date_to)
            query += """ and aml.date <= %s"""

        if partner_id:
            query += """ and aml.partner_id = """ + str(partner_id)

        if journal_id:
            query += """ and aml.journal_id = """ + str(journal_id)

        if user_id:
            query += """ and aml.create_uid = """ + str(user_id)

        if company_id:
            query += """ and aml.company_id = """ + str(company_id)

        query += """
        group by am.name, rp.id, rp.name, aml.name, rp.mobile, aml.date, aj.name
        order by aml.date"""

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

        # domain = [('is_internal_transfer', '=', True)]

        # domain.append(('payment_type', '=', 'outbound')) if payment_type == 'Receipt' else domain.append(
        #     ('payment_type', '=', 'intbound'))

        # domain.append(('state', '=', 'posted'))

        # if date_from:
        #     domain.append(('date', '>=', date_from))

        # if date_to:
        #     domain.append(('date', '<=', date_to))

        # if partner_id:
        #     domain.append(('partner_id', '=', partner_id))

        # if journal_id:
        #     domain.append(('journal_id', '=', journal_id))

        # if user_id:
        #     domain.append(('create_uid', '=', user_id))

        # if company_id:
        #     domain.append(('company_id', '=', company_id))

        # res = self.env['account.payment'].search(domain)
        # return res

    @ api.model
    # def _get_report_values(self, docids, data=None):
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to'],
            'partner_id': data['form']['partner_id'],
            'journal_id': data['form']['journal_id'],
            'user_id': data['form']['user_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'payment_type': data['form']['payment_type'],
            'lines': self._lines,
        }
