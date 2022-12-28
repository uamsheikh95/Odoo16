from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO


class SaleReport(models.Model):
    _inherit = 'sale.report'

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (
            self._table, self._query()))


class SalesByCustomerDetail(models.TransientModel):
    _name = 'mgs_sale.sales_by_customer'
    _description = 'Sales by Customer Detail'

    partner_id = fields.Many2one('res.partner', string="Partner")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    report_by = fields.Selection(
        [('Summary', 'Summary'), ('Detail', 'Detail')], string='Report Type', default='Detail')
    user_id = fields.Many2one('res.users', string='Salesperson')
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
                'user_id': [self.user_id.id, self.user_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
            },
        }

        return self.env.ref('mgs_sale.action_sales_by_customer').report_action(self, data=data)

    def export_to_excel(self):
        sales_by_customer_report_obj = self.env['report.mgs_sale.sales_by_customer_report']
        lines = sales_by_customer_report_obj._lines
        # self, self.date_from, self.date_to, self.company_id.id, self.partner_id.id, self.user_id.id, is_group

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'SalesByCustomer'
        worksheet = workbook.add_worksheet(filename)

        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
        cell_text_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12})
        cell_number_format = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12})
        align_right = workbook.add_format(
            {'align': 'right', 'num_format': '#,##0.00'})
        align_right_money = workbook.add_format(
            {'align': 'right', 'num_format': '$#,##0.00'})
        align_right_money_total = workbook.add_format(
            {'align': 'right', 'bold': True, 'num_format': '$#,##0.00'})
        align_right_total = workbook.add_format(
            {'align': 'right', 'bold': True, 'num_format': '#,##0.00'})
        date_heading_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
        date_format = workbook.add_format(
            {'align': 'left', 'num_format': 'd-m-yyyy'})

        # Heading
        row = 1
        worksheet.merge_range(
            'A1:K1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range('A2:K3', 'Sales by Customer', heading_format)

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

        if self.user_id:
            row += 1
            worksheet.write(row, column+1, 'Salesperson', cell_text_format)
            worksheet.write(row, column+2, self.user_id.name or '')
        column+2

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Customer', cell_text_format)

        worksheet.write(row, column+2, 'Ordered Qty', cell_number_format)
        worksheet.write(row, column+3, 'Delivered Qty', cell_number_format)
        worksheet.write(row, column+4, 'Invoiced Qty', cell_number_format)
        worksheet.write(row, column+5, 'Amount', cell_number_format)

        if self.env.user.has_group('account.group_account_manager'):
            worksheet.write(row, column+6, 'T.Cost', cell_number_format)
            worksheet.write(row, column+7, 'Gross Profit', cell_number_format)

        if self.report_by == 'Detail':
            worksheet.write(row, column+2, 'Date', cell_text_format)
            worksheet.write(row, column+3, 'Order', cell_text_format)
            worksheet.write(row, column+4, 'Item', cell_text_format)

            worksheet.write(row, column+5, 'Ordered Qty', cell_number_format)
            worksheet.write(row, column+6, 'Delivered Qty', cell_number_format)
            worksheet.write(row, column+7, 'Invoiced Qty', cell_number_format)

            worksheet.write(row, column+8, 'Rate', cell_number_format)
            worksheet.write(row, column+9, 'Amount', cell_number_format)

            if self.env.user.has_group('account.group_account_manager'):
                worksheet.write(row, column+10, 'T.Cost', cell_number_format)
                worksheet.write(row, column+11, 'Gross Profit',
                                cell_number_format)

        # Lines
        for main in lines(self.date_from, self.date_to, self.company_id.id, self.partner_id.id, self.user_id.id, 'all'):
            # ------------------------------ Customer ------------------------------

            for partner in lines(self.date_from, self.date_to, self.company_id.id, self.partner_id.id, self.user_id.id, 'yes'):

                if self.report_by == 'Summary':
                    row += 1
                    column = -1
                    worksheet.write(row, column+1, partner['partner_name'])
                    worksheet.write(
                        row, column+2, int(partner['total_qty_ordered']), align_right)
                    worksheet.write(
                        row, column+3, int(partner['total_qty_delivered']), align_right)
                    worksheet.write(
                        row, column+4, int(partner['total_qty_invoiced']), align_right)
                    worksheet.write(
                        row, column+5, int(partner['total_amount']), align_right_money)
                    if self.env.user.has_group('account.group_account_manager'):
                        worksheet.write(
                            row, column+6, int(partner['total_cost']), align_right_money)
                        worksheet.write(
                            row, column+7, int(partner['total_margin']), align_right_money)

                if self.report_by == 'Detail':
                    row += 2
                    column = -1
                    row_number = 'A%s:K%s' % (row, row)
                    worksheet.merge_range(
                        row_number, partner['partner_name'], cell_text_format)

                    # ------------------------------ Lines ------------------------------
                    for line in lines(self.date_from, self.date_to, self.company_id.id, partner['partner_id'], self.user_id.id, 'no'):
                        row += 1
                        column = -1

                        worksheet.write(row, column+1, '')
                        worksheet.write(
                            row, column+2, line['date'], date_format)
                        worksheet.write(row, column+3, line['order_no'])
                        worksheet.write(
                            row, column+4, line['product']['en_US'])
                        worksheet.write(
                            row, column+5, int(line['product_uom_qty']), align_right)
                        worksheet.write(
                            row, column+6, int(line['qty_delivered']), align_right)
                        worksheet.write(
                            row, column+7, int(line['qty_invoiced']), align_right)

                        worksheet.write(
                            row, column+8, line['price_total']/line['product_uom_qty'], align_right)
                        worksheet.write(
                            row, column+9, int(line['price_total']), align_right_money)

                        if self.env.user.has_group('account.group_account_manager'):
                            worksheet.write(
                                row, column+10, int(line['cost']), align_right_money)
                            worksheet.write(
                                row, column+11, int(line['margin']), align_right_money)

                        # ---------------------------------------- END LINES ----------------------------------------

                    row += 2
                    column = -1
                    worksheet.write(row, column+1, 'TOTAL ' +
                                    partner['partner_name'], cell_text_format)
                    worksheet.write(row, column+2, '', cell_text_format)
                    worksheet.write(row, column+3, '', cell_text_format)
                    worksheet.write(row, column+4, '', cell_text_format)
                    worksheet.write(
                        row, column+5, int(partner['total_qty_ordered']), align_right_total)
                    worksheet.write(
                        row, column+6, int(partner['total_qty_delivered']), align_right_total)
                    worksheet.write(
                        row, column+7, int(partner['total_qty_invoiced']), align_right_total)
                    worksheet.write(row, column+8, '')
                    worksheet.write(
                        row, column+9, int(partner['total_amount']), align_right_money_total)

                    if self.env.user.has_group('account.group_account_manager'):
                        worksheet.write(
                            row, column+10, int(partner['total_cost']), align_right_money_total)
                        worksheet.write(
                            row, column+11, int(partner['total_margin']), align_right_money_total)

            # Main Totals
            row += 2
            column = -1
            worksheet.write(row, column+1, 'Total', cell_text_format)

            worksheet.write(
                row, column+2, int(main['total_qty_ordered_all']), align_right_total)
            worksheet.write(
                row, column+3, int(main['total_qty_delivered_all']), align_right_total)
            worksheet.write(
                row, column+4, int(main['total_qty_invoiced_all']), align_right_total)
            worksheet.write(
                row, column+5, int(main['total_amount_all']), align_right_money_total)

            if self.env.user.has_group('account.group_account_manager'):
                worksheet.write(
                    row, column+6, int(main['total_cost_all']), align_right_money_total)
                worksheet.write(
                    row, column+7, int(main['total_margin_all']), align_right_money_total)

            if self.report_by == 'Detail':
                worksheet.write(row, column+2, '', cell_text_format)
                worksheet.write(row, column+3, '', cell_text_format)
                worksheet.write(row, column+4, '', cell_text_format)

                worksheet.write(
                    row, column+5, int(main['total_qty_ordered_all']), align_right_total)
                worksheet.write(
                    row, column+6, int(main['total_qty_delivered_all']), align_right_total)
                worksheet.write(
                    row, column+7, int(main['total_qty_invoiced_all']), align_right_total)
                worksheet.write(row, column+8, '', cell_number_format)
                worksheet.write(
                    row, column+9, int(main['total_amount_all']), align_right_money_total)

                if self.env.user.has_group('account.group_account_manager'):
                    worksheet.write(
                        row, column+10, int(main['total_cost_all']), align_right_money_total)
                    worksheet.write(
                        row, column+11, int(main['total_margin_all']), align_right_money_total)

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


class SalesByCustomerDetailReport(models.AbstractModel):
    _name = 'report.mgs_sale.sales_by_customer_report'
    _description = 'Sales by Customer Detail Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id, user_id, is_group):  # , company_branch_ids
        full_move = []
        params = []

        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"

        if is_group == 'all':
            select = """select
            COALESCE(sum(sr.product_uom_qty), 0) as total_qty_ordered_all, COALESCE(sum(sr.qty_delivered), 0) as total_qty_delivered_all,
            COALESCE(sum(sr.qty_invoiced), 0) as total_qty_invoiced_all, COALESCE(sum(sr.qty_to_invoice), 0) as total_qty_to_invoice_all,
            COALESCE(sum(sr.price_total), 0) as total_amount_all, COALESCE(sum(sr.price_total-sr.margin), 0) as total_cost_all,
            COALESCE(sum(sr.margin), 0) as total_margin_all"""
            order = ""

        if is_group == 'yes':
            select = """select rp.name as partner_name, rp.id as partner_id,
            COALESCE(sum(sr.product_uom_qty), 0) as total_qty_ordered, COALESCE(sum(sr.qty_delivered), 0) as total_qty_delivered,
            COALESCE(sum(sr.qty_invoiced), 0) as total_qty_invoiced, COALESCE(sum(sr.qty_to_invoice), 0) as total_qty_to_invoice,
            COALESCE(sum(sr.price_total), 0) as total_amount, COALESCE(sum(sr.price_total-sr.margin), 0) as total_cost,
            COALESCE(sum(sr.margin), 0) as total_margin"""
            order = """
            group by rp.name, rp.id
            order by rp.name
            """

        if is_group == 'no':
            select = """
            select sr.date, sr.name as order_no, pt.name as product, salesperson.name as salesperson,
            COALESCE(sr.product_uom_qty, 0) as product_uom_qty, COALESCE(sr.qty_delivered, 0) as qty_delivered, COALESCE(sr.qty_invoiced, 0) as qty_invoiced, COALESCE(sr.qty_to_invoice, 0) as qty_to_invoice, COALESCE(sr.price_total, 0) as price_total,
            sr.state, COALESCE(sr.price_total-sr.margin, 0) as cost, COALESCE(sr.margin, 0) as margin
            """

            order = """
            order by sr.date
            """
        from_where = """
        from sale_report as sr
        left join res_partner as rp on sr.partner_id=rp.id
        left join product_product as pp on sr.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        left join res_users ru on sr.user_id=ru.id
        left join res_partner salesperson on ru.partner_id=salesperson.id
        where sr.state in ('sale', 'done', 'paid', 'pos_done', 'invoiced')
        """

        if date_from:
            params.append(f_date)
            from_where += """ and sr.date >= %s"""

        if date_to:
            params.append(t_date)
            from_where += """ and sr.date <= %s"""

        if partner_id:
            from_where += """ and sr.partner_id = """ + str(partner_id)

        if user_id:
            from_where += """ and sr.user_id = """ + str(user_id)

        if company_id:
            from_where += """ and sr.company_id = """ + str(company_id)

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
            'user_id': data['form']['user_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'lines': self._lines,
        }
