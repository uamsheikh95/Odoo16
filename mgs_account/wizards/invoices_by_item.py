from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO


class InvoicesbyItem(models.TransientModel):
    _name = 'mgs_account.invoices_by_item'
    _description = 'Invoices by Item'

    product_id = fields.Many2one('product.product', string="Product")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    invoices_bills = fields.Selection([('Invoices', 'Invoices'), (
        'Bills', 'Bills')], string='Invoices/Bills', default='Invoices', required=True)
    report_by = fields.Selection([('Summary', 'Summary'), ('Detail', 'Detail')],
                                 string='Report Type', default='Detail', required=True)
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_the_date_from_and_to(self):
        if self.date_to and self.date_from and self.date_to < self.date_from:
            raise ValidationError('''From Date should be less than To Date.''')

    def confirm(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'product_id': [self.product_id.id, self.product_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
                'invoices_bills': self.invoices_bills,
            },
        }

        return self.env.ref('mgs_account.action_invoices_by_item').report_action(self, data=data)

    def export_to_excel(self):
        invoices_by_item_report_obj = self.env['report.mgs_account.invoices_by_item_report']
        lines = invoices_by_item_report_obj._lines

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'InvoicesByItem'
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
        worksheet.merge_range('A2:G3', 'Invoices by Item', heading_format)

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

        if self.product_id:
            row += 1
            worksheet.write(row, column+1, 'Product', cell_text_format)
            worksheet.write(row, column+2, self.product_id.name or '')
        column+2

        if self.invoices_bills:
            row += 1
            worksheet.write(row, column+1, 'Invoices/Bills', cell_text_format)
            worksheet.write(row, column+2, self.invoices_bills or '')
        column+2

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Item', cell_text_format)

        worksheet.write(row, column+2, 'Ordered Qty', cell_number_format)
        worksheet.write(row, column+3, 'Amount', cell_number_format)

        if self.report_by == 'Detail':
            worksheet.write(row, column+2, 'Date', cell_text_format)
            worksheet.write(row, column+3, 'Order', cell_text_format)
            worksheet.write(row, column+4, 'Partner', cell_text_format)

            worksheet.write(row, column+5, 'Qty', cell_number_format)
            worksheet.write(row, column+6, 'Rate', cell_number_format)
            worksheet.write(row, column+7, 'Amount', cell_number_format)

        # Lines
        for main in lines(self.date_from, self.date_to, self.company_id.id, self.product_id.id, 'all', self.invoices_bills):
            # ------------------------------ Item ------------------------------

            for product in lines(self.date_from, self.date_to, self.company_id.id, self.product_id.id, 'yes', self.invoices_bills):

                if self.report_by == 'Summary':
                    row += 1
                    column = -1
                    worksheet.write(
                        row, column+1, product['product_name']['en_US'])
                    worksheet.write(
                        row, column+2, int(product['total_qty']), align_right)
                    worksheet.write(
                        row, column+3, int(product['total_amount']), align_right)

                if self.report_by == 'Detail':
                    row += 2
                    column = -1
                    row_number = 'A%s:C%s' % (row, row)
                    worksheet.merge_range(
                        row_number, product['product_name']['en_US'], cell_text_format)

                    # ------------------------------ Lines ------------------------------
                    for line in lines(self.date_from, self.date_to, self.company_id.id, product['product_id'], 'no', self.invoices_bills):
                        row += 1
                        column = -1

                        worksheet.write(row, column+1, '')
                        worksheet.write(
                            row, column+2, line['date'], date_format)
                        worksheet.write(row, column+3, line['ref'])
                        worksheet.write(row, column+4, line['partner'])
                        worksheet.write(
                            row, column+5, int(line['quantity']), align_right)
                        worksheet.write(
                            row, column+6, line['amount_total']/line['quantity'], align_right)
                        worksheet.write(
                            row, column+7, int(line['amount_total']), align_right)

                        # ---------------------------------------- END LINES ----------------------------------------

                    row += 2
                    column = -1
                    worksheet.write(row, column+1, 'TOTAL ' +
                                    product['product_name']['en_US'], cell_text_format)
                    worksheet.write(row, column+2, '')
                    worksheet.write(row, column+3, '')
                    worksheet.write(row, column+4, '')
                    worksheet.write(
                        row, column+5, int(product['total_qty']), align_right_total)
                    worksheet.write(row, column+6, '')
                    worksheet.write(
                        row, column+7, int(product['total_amount']), align_right_total)

            # Main Totals
            row += 2
            column = -1
            worksheet.write(row, column+1, 'Total', cell_text_format)

            worksheet.write(
                row, column+2, int(main['total_qty_all']), align_right_total)
            worksheet.write(
                row, column+3, int(main['total_amount_all']), align_right_total)

            if self.report_by == 'Detail':
                worksheet.write(row, column+2, '', cell_text_format)
                worksheet.write(row, column+3, '', cell_text_format)
                worksheet.write(row, column+4, '', cell_text_format)

                worksheet.write(
                    row, column+5, int(main['total_qty_all']), align_right_total)
                worksheet.write(row, column+6, '', align_right_total)
                worksheet.write(
                    row, column+7, int(main['total_amount_all']), align_right_total)

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


class InvoicesbyItemReport(models.AbstractModel):
    _name = 'report.mgs_account.invoices_by_item_report'
    _description = 'Invoices by Item Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, product_id, is_group, invoices_bills):  # , company_branch_ids
        full_move = []
        params = []
        types = """('out_invoice', 'out_refund')"""

        if invoices_bills == 'Bills':
            types = """('in_invoice', 'in_refund')"""

        if is_group == 'all':
            select = """select COALESCE(sum(air.quantity), 0) as total_qty_all, COALESCE(sum(air.price_subtotal), 0) as total_amount_all"""
            order = ""

        if is_group == 'yes':
            select = """select pt.name as product_name, pp.id as product_id, COALESCE(sum(air.quantity), 0) as total_qty, COALESCE(sum(air.price_subtotal), 0) as total_amount"""
            order = """
            group by pt.name, pp.id
            order by pt.name
            """

        if is_group == 'no':
            select = """
            select air.invoice_date as date, concat(am.invoice_origin,' - ', am.name) as ref, rp.name as partner,
            am.id as move_id, pp.id as product_id,
            air.quantity as quantity, air.price_subtotal as amount_total, air.price_average as rate, air.state as state
            """

            order = """
            order by air.invoice_date
            """
        from_where = """
        from account_invoice_report as air
        left join account_move as am on air.move_id=am.id
        left join res_partner as rp on air.partner_id=rp.id
        left join product_product as pp on air.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        where air.state = 'posted' and air.quantity != 0
        and air.move_type in """ + types

        if date_from:
            params.append(date_from)
            from_where += """ and air.invoice_date >= %s"""

        if date_to:
            params.append(date_to)
            from_where += """ and air.invoice_date <= %s"""

        if product_id:
            from_where += """ and air.product_id = """ + str(product_id)

        if company_id:
            from_where += """ and air.company_id = """ + str(company_id)

        query = select + from_where + order

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

    # @api.model
    # def _get_cogs(self, move_id, product_id):
    #     params = [move_id, product_id, 'Cost of Revenue']
    #     query = """
    #     select sum(aml.debit) from account_move_line aml
    #     left join account_account aa on aml.account_id=aa.id
    #     left join account_account_type aat on aa.user_type_id=aat.id
    #     where aml.move_id = %s and aml.product_id = %s
    #     and aat.name = %s
    #     """
    #
    #     self.env.cr.execute(query, tuple(params))
    #
    #     contemp = self.env.cr.fetchone()
    #     if contemp is not None:
    #         result = contemp[0] or 0.0
    #     return result

    @api.model
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
            'product_id': data['form']['product_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'invoices_bills': data['form']['invoices_bills'],
            'lines': self._lines,
            # 'get_cogs': self._get_cogs
        }
