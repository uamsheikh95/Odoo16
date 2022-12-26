from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO


class InvoicesbyPartner(models.TransientModel):
    _name = 'mgs_account.invoices_by_partner'
    _description = 'Invoices by Partner'

    partner_id = fields.Many2one('res.partner', string="Partner")
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
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
                'invoices_bills': self.invoices_bills,
            },
        }

        return self.env.ref('mgs_account.action_invoices_by_partner').report_action(self, data=data)

    def export_to_excel(self):
        invoices_by_partner_report_obj = self.env['report.mgs_account.invoices_by_partner_report']
        lines = invoices_by_partner_report_obj._lines

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'InvoicesByPartner'
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
        worksheet.merge_range('A2:G3', 'Invoices by Partner', heading_format)

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

        if self.partner_id:
            row += 1
            worksheet.write(row, column+1, 'Partner', cell_text_format)
            worksheet.write(row, column+2, self.partner_id.name or '')
        column+2

        if self.invoices_bills:
            row += 1
            worksheet.write(row, column+1, 'Invoices/Bills', cell_text_format)
            worksheet.write(row, column+2, self.invoices_bills or '')
        column+2

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Partner', cell_text_format)

        worksheet.write(row, column+2, 'Ordered Qty', cell_number_format)
        worksheet.write(row, column+3, 'Amount', cell_number_format)

        if self.report_by == 'Detail':
            worksheet.write(row, column+2, 'Date', cell_text_format)
            worksheet.write(row, column+3, 'Order', cell_text_format)
            worksheet.write(row, column+4, 'Item', cell_text_format)

            worksheet.write(row, column+5, 'Qty', cell_number_format)
            worksheet.write(row, column+6, 'Rate', cell_number_format)
            worksheet.write(row, column+7, 'Amount', cell_number_format)

        # Lines
        for main in lines(self.date_from, self.date_to, self.company_id.id, self.partner_id.id, 'all', self.invoices_bills):
            # ------------------------------ Partner ------------------------------

            for partner in lines(self.date_from, self.date_to, self.company_id.id, self.partner_id.id, 'yes', self.invoices_bills):

                if self.report_by == 'Summary':
                    row += 1
                    column = -1
                    worksheet.write(row, column+1, partner['partner_name'])
                    worksheet.write(
                        row, column+2, "{:,}".format(partner['total_qty']), align_right)
                    worksheet.write(
                        row, column+3, "{:,}".format(partner['total_amount']), align_right)

                if self.report_by == 'Detail':
                    row += 2
                    column = -1
                    row_number = 'A%s:C%s' % (row, row)
                    worksheet.merge_range(
                        row_number, partner['partner_name'], cell_text_format)

                    # ------------------------------ Lines ------------------------------
                    for line in lines(self.date_from, self.date_to, self.company_id.id, partner['partner_id'], 'no', self.invoices_bills):
                        row += 1
                        column = -1

                        worksheet.write(row, column+1, '')
                        worksheet.write(
                            row, column+2, line['date'], date_format)
                        worksheet.write(row, column+3, line['ref'])
                        worksheet.write(row, column+4, line['product'])
                        worksheet.write(
                            row, column+5, "{:,}".format(line['quantity']), align_right)
                        worksheet.write(
                            row, column+6, line['amount_total']/line['quantity'], align_right)
                        worksheet.write(
                            row, column+7, "{:,}".format(line['amount_total']), align_right)

                        # ---------------------------------------- END LINES ----------------------------------------

                    row += 2
                    column = -1
                    worksheet.write(row, column+1, 'TOTAL ' +
                                    partner['partner_name'], cell_text_format)
                    worksheet.write(row, column+2, '')
                    worksheet.write(row, column+3, '')
                    worksheet.write(row, column+4, '')
                    worksheet.write(
                        row, column+5, "{:,}".format(partner['total_qty']), align_right_total)
                    worksheet.write(row, column+6, '')
                    worksheet.write(
                        row, column+7, "{:,}".format(partner['total_amount']), align_right_total)

            # Main Totals
            row += 2
            column = -1
            worksheet.write(row, column+1, 'Total', cell_text_format)

            worksheet.write(
                row, column+2, "{:,}".format(main['total_qty_all']), align_right_total)
            worksheet.write(
                row, column+3, "{:,}".format(main['total_amount_all']), align_right_total)

            if self.report_by == 'Detail':
                worksheet.write(row, column+2, '', cell_text_format)
                worksheet.write(row, column+3, '', cell_text_format)
                worksheet.write(row, column+4, '', cell_text_format)

                worksheet.write(
                    row, column+5, "{:,}".format(main['total_qty_all']), align_right_total)
                worksheet.write(row, column+6, '', align_right_total)
                worksheet.write(
                    row, column+7, "{:,}".format(main['total_amount_all']), align_right_total)

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


class InvoicesbyPartnerReport(models.AbstractModel):
    _name = 'report.mgs_account.invoices_by_partner_report'
    _description = 'Invoices by Partner Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id, is_group, invoices_bills):  # , company_branch_ids
        full_move = []
        params = []
        types = """('out_invoice', 'out_refund')"""

        if invoices_bills == 'Bills':
            types = """('in_invoice', 'in_refund')"""

        if is_group == 'all':
            select = """select COALESCE(sum(air.quantity), 0) as total_qty_all, COALESCE(sum(air.price_subtotal), 0) as total_amount_all"""
            order = ""

        if is_group == 'yes':
            select = """select rp.name as partner_name, rp.id as partner_id, COALESCE(sum(air.quantity), 0) as total_qty, COALESCE(sum(air.price_subtotal), 0) as total_amount"""
            order = """
            group by rp.name, rp.id
            order by rp.name
            """

        if is_group == 'no':
            select = """
            select air.invoice_date as date, concat(am.invoice_origin,' - ', am.name) as ref, pt.name as product,
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

        if partner_id:
            from_where += """ and air.partner_id = """ + str(partner_id)

        if company_id:
            from_where += """ and air.company_id = """ + str(company_id)

        query = select + from_where + order

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

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
            'partner_id': data['form']['partner_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'invoices_bills': data['form']['invoices_bills'],
            'lines': self._lines,
        }
