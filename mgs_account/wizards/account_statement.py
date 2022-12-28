# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo import models, fields, api
import xlsxwriter
import base64
from io import BytesIO


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
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

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

    def export_to_excel(self):
        account_statement_report_obj = self.env['report.mgs_account.account_statement_report']
        lines = account_statement_report_obj._lines
        sum_open_balance = account_statement_report_obj._sum_open_balance

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'AccountStatement'
        worksheet = workbook.add_worksheet(filename)

        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
        cell_text_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12})
        cell_number_format = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12})
        align_right = workbook.add_format({'align': 'right'})
        align_right_total = workbook.add_format(
            {'align': 'right', 'bold': True})
        date_heading_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
        date_format = workbook.add_format(
            {'align': 'left', 'num_format': 'd-m-yyyy'})

        # Heading
        row = 1
        worksheet.merge_range(
            'A1:I1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range('A2:I3', 'Account Statement', heading_format)

        # Search criteria
        row += 2
        column = -1
        if self.date_from:
            row += 1
            worksheet.write(row, column+1, 'From Date', cell_text_format)
            worksheet.write(row, column+2, self.date_from or '',
                            date_heading_format)
        column+2

        if self.date_to:
            row += 1
            worksheet.write(row, column+1, 'To Date', cell_text_format)
            worksheet.write(row, column+2, self.date_to or '',
                            date_heading_format)
        column+2

        # if self.user_type_id:
        #     row += 1
        #     worksheet.write(row, column+1, 'Account Type', cell_text_format)
        #     worksheet.write(row, column+2, self.user_type_id.name or '')
        column+2

        if self.target_moves:
            row += 1
            worksheet.write(row, column+1, 'Target Moves', cell_text_format)
            worksheet.write(row, column+2, self.target_moves or '')
        column+2

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Account', cell_text_format)

        worksheet.write(row, column+2, 'Initial Balance', cell_number_format)
        worksheet.write(row, column+3, 'Debit', cell_number_format)
        worksheet.write(row, column+4, 'Credit', cell_number_format)
        worksheet.write(row, column+5, 'Balance', cell_number_format)

        if self.report_by == 'detail':
            worksheet.write(row, column+2, 'Date', cell_text_format)
            worksheet.write(row, column+3, 'JV#', cell_text_format)
            worksheet.write(row, column+4, 'Partner', cell_text_format)
            worksheet.write(row, column+5, 'Label', cell_text_format)
            worksheet.write(row, column+6, 'Debit', align_right_total)
            worksheet.write(row, column+7, 'Credit', align_right_total)
            worksheet.write(row, column+8, 'Balance', align_right_total)

            if self.env.user.has_group('analytic.group_analytic_accounting'):
                worksheet.write(
                    row, column+5, 'Analytic Account', cell_number_format)
                worksheet.write(row, column+6, 'Label', cell_number_format)
                worksheet.write(row, column+7, 'Debit', align_right_total)
                worksheet.write(row, column+8, 'Credit', align_right_total)
                worksheet.write(row, column+9, 'Balance', align_right_total)

        # ------------------------------ Account ------------------------------
        total_debit_all = 0
        total_credit_all = 0

        for account in lines(self.company_id.id, self.date_from, self.date_to, self.account_id.id, self.partner_id.id, self.analytic_account_id.id, self.target_moves, 'yes'):
            # Inital Balance
            initial_balance = 0 if not self.date_from else sum_open_balance(
                self.company_id.id, self.date_from, account['account_id'], self.analytic_account_id.id, self.partner_id.id, self.target_moves)
            total_balance = initial_balance + \
                (account['total_debit']-account['total_credit'])
            balance = initial_balance
            if self.report_by == 'summary':
                row += 1
                column = -1
                worksheet.write(row, column+1, account['group'])
                worksheet.write(
                    row, column+2, int(initial_balance), align_right)
                worksheet.write(
                    row, column+3, int(account['total_debit']), align_right)
                worksheet.write(
                    row, column+4, int(account['total_credit']), align_right)
                worksheet.write(
                    row, column+5, int(total_balance), align_right)

                total_debit_all += account['total_debit']
                total_credit_all += account['total_credit']

            if self.report_by == 'detail':
                row += 2
                column = -1
                worksheet.write(
                    row, column+1, account['group'], cell_text_format)
                worksheet.write(
                    row, column+8, int(initial_balance), align_right_total)

                # ------------------------------ Lines ------------------------------
                for line in lines(self.company_id.id, self.date_from, self.date_to, account['account_id'], self.partner_id.id, self.analytic_account_id.id, self.target_moves, 'no'):
                    row += 1
                    column = -1

                    worksheet.write(row, column+1, '')
                    worksheet.write(row, column+2, line['date'], date_format)
                    worksheet.write(row, column+3, line['voucher_no'])
                    worksheet.write(row, column+4, line['partner_name'])
                    worksheet.write(row, column+5, line['label'])
                    worksheet.write(
                        row, column+6, int(line['debit']), align_right)
                    worksheet.write(
                        row, column+7, int(line['credit']), align_right)
                    balance += line['debit'] - line['credit']
                    worksheet.write(
                        row, column+8, int(balance), align_right)

                    # ---------------------------------------- END LINES ----------------------------------------

                row += 1
                column = -1
                worksheet.write(row, column+1, 'TOTAL ' +
                                account['group'], cell_text_format)
                worksheet.write(
                    row, column+6, int(account['total_debit']), align_right_total)
                worksheet.write(
                    row, column+7, int(account['total_credit']), align_right_total)
                worksheet.write(
                    row, column+8, int(total_balance), align_right_total)

        row += 1
        column = -1
        worksheet.write(row, column+1, '')
        worksheet.write(
            row, column+7, int(total_debit_all), align_right_total)
        worksheet.write(
            row, column+8, int(total_credit_all), align_right_total)
        worksheet.write(
            row, column+9, int(total_debit_all-total_credit_all), align_right_total)

        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        self.write({'datas': out, 'datas_fname': filename})
        fp.close()
        filename += '%2Exlsx'

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model='+self._name+'&id='+str(self.id)+'&field=datas&download=true&filename='+filename,
        }


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
            aml.partner_id, aml.account_id, aml.debit as debit, aml.credit as credit, am.ref as move_ref
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

        # if analytic_account_id:
        #     query += """ and aml.analytic_account_id = """ + \
        #         str(analytic_account_id)

        if analytic_account_id:
            # from_where_query += """ and aaa.id = """ + \
            #     str(analytic_account_id)
            query += ' and aml.analytic_distribution @> \'{"%s": 100}\'::jsonb' % str(
                analytic_account_id)

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
