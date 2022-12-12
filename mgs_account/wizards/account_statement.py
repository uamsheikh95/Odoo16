# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo import models, fields, api


class AccountStatement(models.TransientModel):
    _name = 'mgs_account.account_statement'
    _description = 'Account Statement Wizard'

    account_id = fields.Many2one('account.account', string="Account")
    partner_id = fields.Many2many('res.partner', string="Partner")
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account')
    date_from = fields.Date(
        'From  Date', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To  Date', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id)
    report_by = fields.Selection(
        [('detail', 'Detail'), ('summary', 'Summary')], string='Report Type', default='detail')
    target_moves = fields.Selection(
        [('all', 'All Entries'), ('posted', 'All Posted Entries')], string='Target Moves', default='all')

    # @api.multi

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'company_id': [self.company_id.id, self.company_id.name],
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'account_id': [self.account_id.id, self.account_id.name],
                'analytic_account_id': [self.analytic_account_id.id, self.analytic_account_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'report_by': self.report_by,
                'target_moves': self.target_moves
            },
        }

        return self.env.ref('mgs_account.action_report_account_statement').report_action(self, data=data)


class AccountStatementReport(models.AbstractModel):
    _name = 'report.mgs_account.account_statement_report'
    _description = 'Account Statement Report'

    def _lines(self, company_id, date_from, date_to, account_id, partner_id, analytic_account_id, target_moves, is_it_group):
        params = []
        states = """('posted','draft')"""
        if target_moves == 'posted':
            states = """('posted')"""

        if is_it_group == 'yes':
            select_query = """
            select concat(aa.code,' - ', aa.name) as group, aa.name as account_name, aa.id as account_id, sum(aml.debit) as total_debit, sum(aml.credit) total_credit
            """

            order_query = """
            group by concat(aa.code,' - ', aa.name), aa.name, aa.id
            order by aa.code
            """

        if is_it_group == 'no':
            select_query = """
            select aml.id, aml.date as date, aml.move_id as move_id, aj.name as voucher_type,
            rp.name as partner_name, aml.name as label, aml.ref as ref, am.name as voucher_no,
            aml.partner_id, aml.account_id, aml.debit as debit, aml.credit as credit,
            aaa.name as analytic_account_name, am.ref as move_ref
            """

            order_query = """
            order by aml.date
            """

        from_where_query = """
        from account_move_line as aml
        left join account_account as aa on aml.account_id=aa.id
        left join res_partner as rp on aml.partner_id=rp.id
        left join account_move as am on aml.move_id=am.id
        left join account_journal as aj on aml.journal_id=aj.id
        left join account_analytic_account as aaa on cast(jsonb_object_keys(aml.analytic_distribution) as Integer)=aaa.id
        where am.state in """ + states

        if date_from:
            params.append(date_from)
            from_where_query += """ and aml.date >= %s"""

        if date_to:
            params.append(date_to)
            from_where_query += """ and aml.date <= %s"""

        if account_id:
            from_where_query += """ and aml.account_id = """ + str(account_id)

        if analytic_account_id:
            # from_where_query += """ and aaa.id = """ + \
            #     str(analytic_account_id)
            from_where_query += ' and aml.analytic_distribution @> \'{"%s": 100}\'::jsonb' % str(
                analytic_account_id)

        if partner_id:
            from_where_query += """ and aml.partner_id = """ + str(partner_id)

        if company_id:
            from_where_query += """ and aml.company_id = """ + str(company_id)

        query = select_query + from_where_query + order_query

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

    def _sum_open_balance(self, company_id, date_from, account_id, analytic_account_id, partner_id, target_moves):
        states = """('posted','draft')"""
        if target_moves == 'posted':
            states = """('posted')"""

        params = [account_id, date_from, company_id]
        query = """
            select sum(aml.debit-aml.credit)
            from account_move_line  as aml
            left join account_move as am on aml.move_id=am.id
            where aml.account_id = %s and aml.date < %s and am.state in """ + states + """
            and aml.company_id = %s"""

        if analytic_account_id:
            query += """ and aml.analytic_account_id = """ + \
                str(analytic_account_id)

        if partner_id:
            query += """ and aml.partner_id = """ + str(partner_id)

        if partner_id:
            query += """ and aml.partner_id = """ + str(partner_id)

        self.env.cr.execute(query, tuple(params))
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to'],
            'account_id': data['form']['account_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'target_moves': data['form']['target_moves'],
            'analytic_account_id': data['form']['analytic_account_id'],
            'partner_id': data['form']['partner_id'],
            'sum_open_balance': self._sum_open_balance,
            'lines': self._lines,
        }
