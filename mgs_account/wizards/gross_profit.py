# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo import models, fields, api
import xlsxwriter
import base64
from io import BytesIO


class GrossProfit(models.TransientModel):
    _name = 'mgs_account.gross_profit'
    _description = 'Gross Profit Wizard'

    product_id = fields.Many2one('product.product', string="Product")
    partner_id = fields.Many2one('res.partner', string="Partner")
    # , default=lambda self: fields.Date.today().replace(day=1)
    date_from = fields.Date('From Date')
    # , default=lambda self: fields.Date.today()
    date_to = fields.Date('To Date')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id, required=True)
    report_by = fields.Selection(
        [('Product', 'Product'), ('Partner', 'Partner')], string='Group by', default='Product', required=True)
    target_moves = fields.Selection(
        [('all', 'All Entries'), ('posted', 'All Posted Entries')], string='Target Moves', default='all', required=True)
    product_type = fields.Selection([('all', 'All Products'), ('product', '	Storable Products'), (
        'service', 'Service Products')], string='Product Type', default='all', required=True)
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'company_id': [self.company_id.id, self.company_id.name],
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'product_id': [self.product_id.id, self.product_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'report_by': self.report_by,
                'target_moves': self.target_moves,
                'product_type': self.product_type,
            },
        }

        return self.env.ref('mgs_account.action_report_gross_profit').report_action(self, data=data)

    def export_to_excel(self):
        gross_profit_report_obj = self.env['report.mgs_account.gross_profit_report']
        lines = gross_profit_report_obj._lines
        # self, self.date_from, self.date_to, self.company_id.id, self.partner_id.id, self.user_id.id, is_group

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'GrossProfitReports'
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
            'A1:G1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range('A2:G3', 'Gross Profit Report', heading_format)

        # Search criteria
        row += 2
        column = -1
        if self.date_from:
            row += 1
            worksheet.write(row, column+1, 'From Date', cell_text_format)
            worksheet.write(row, column+2, self.date_from or '',
                            date_format)

        if self.date_to:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'To Date', cell_text_format)
            worksheet.write(row, column+2, self.date_to or '',
                            date_format)

        if self.product_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Product', cell_text_format)
            worksheet.write(row, column+2, self.product_id.name or '')

        if self.report_by:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Report by', cell_text_format)
            worksheet.write(row, column+2, self.report_by or '')

        if self.report_by:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Report by', cell_text_format)
            worksheet.write(row, column+2, self.report_by or '')

        if self.target_moves:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Target Moves', cell_text_format)
            worksheet.write(row, column+2, self.target_moves or '')

        if self.product_type:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Product Type', cell_text_format)
            worksheet.write(row, column+2, self.product_type or '')

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'No', cell_text_format)
        worksheet.write(row, column+2, self.report_by, cell_text_format)
        worksheet.write(row, column+3, 'Product Code', cell_text_format)
        worksheet.write(row, column+4, 'Actual Revenue', cell_number_format)
        worksheet.write(row, column+5, 'Actual Cost', cell_number_format)
        worksheet.write(row, column+6, 'Gross Profit', cell_number_format)
        worksheet.write(row, column+7, 'Gross Profit %', cell_number_format)

        no = 0
        total_act_cost = 0
        total_act_revenue = 0

        for line in lines(self.company_id.id, self.date_from, self.date_to, self.partner_id.id, self.product_id.id, self.target_moves, self.product_type, self.report_by):
            row += 2
            column = -1
            no += 1

            worksheet.write(row, column+1, no)
            group = line['group'] if self.report_by == 'Partner' else line['group']['en_US']
            worksheet.write(row, column+2, group)
            worksheet.write(row, column+3, line['default_code'])
            worksheet.write(
                row, column+4, '{:,.2f}'.format(line['act_revenue']), align_right)
            worksheet.write(
                row, column+5, '{:,.2f}'.format(line['act_cost']), align_right)

            balance = line['act_revenue']-line['act_cost']
            balance_percentage = (
                balance/line['act_revenue']) * 100 if line['act_revenue'] else 0
            worksheet.write(
                row, column+6, '{:,.2f}'.format(balance), align_right)
            worksheet.write(
                row, column+7, '{:,.2f}'.format(balance_percentage), align_right)

            total_act_cost += line['act_cost']
            total_act_revenue += line['act_revenue']

        row += 2
        column = -1
        worksheet.write(
            row, column+4, '{:,.2f}'.format(total_act_revenue), cell_number_format)
        worksheet.write(
            row, column+5, '{:,.2f}'.format(total_act_cost), cell_number_format)
        worksheet.write(
            row, column+6, '{:,.2f}'.format(total_act_revenue-total_act_cost), cell_number_format)

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


class GrossProfitReport(models.AbstractModel):
    _name = 'report.mgs_account.gross_profit_report'
    _description = 'Gross Profit Report'

    def _lines(self, company_id, date_from, date_to, partner_id, product_id, target_moves, product_type, report_by):
        params = []
        states = "('posted','draft')"
        if target_moves == 'posted':
            states = "('posted')"

        select_query = """select pt.name as group, pt.default_code as default_code, pp.id as product_id,
        COALESCE(sum(aml.debit), 0) as act_cost,
        COALESCE(sum(aml.credit), 0) as act_revenue"""

        order_query = "group by pt.name, pt.default_code, pp.id order by pt.name"

        if report_by == 'Partner':
            select_query = """select rp.name as group,
            COALESCE(sum(aml.debit), 0) as act_cost,
            COALESCE(sum(aml.credit), 0) as act_revenue"""

            order_query = "group by rp.name order by rp.name"

        from_where_query = """
        from account_move_line as aml
        left join account_account as aa on aml.account_id=aa.id
        left join res_partner as rp on aml.partner_id=rp.id
        left join product_product as pp on aml.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        where aa.account_type in ('expense_direct_cost', 'income') and aml.parent_state in """ + states

        if date_from:
            params.append(date_from)
            from_where_query += " and aml.date >= %s"

        if date_to:
            params.append(date_to)
            from_where_query += " and aml.date <= %s"

        if report_by == 'Product' and product_id:
            from_where_query += " and aml.product_id = " + str(product_id)

            # if product_type == 'product':
            #     from_where_query += " and pt.product_tye = 'product"

            # if product_type == 'service':
            #     from_where_query += " and pt.product_tye = 'service"

        if report_by == 'Partner' and partner_id:
            from_where_query += " and aml.partner_id = " + str(partner_id)

        if company_id:
            from_where_query += " and aml.company_id = " + str(company_id)

        query = select_query + from_where_query + order_query

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

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
            'product_id': data['form']['product_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'target_moves': data['form']['target_moves'],
            'product_type': data['form']['product_type'],
            'partner_id': data['form']['partner_id'],
            'lines': self._lines,
        }
