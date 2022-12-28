from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO


class PurchasesbyItemDetail(models.TransientModel):
    _name = 'mgs_purchase.purchases_by_item'
    _description = 'Purchases by Item'

    product_id = fields.Many2one('product.product', string="Product")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    report_by = fields.Selection(
        [('Summary', 'Summary'), ('Detail', 'Detail')], string='Report Type', default='Detail')
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
            },
        }

        return self.env.ref('mgs_purchase.action_purchases_by_item').report_action(self, data=data)

    def export_to_excel(self):
        purchases_by_item_report_obj = self.env['report.mgs_purchase.purchases_by_item_report']
        lines = purchases_by_item_report_obj._lines

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'PurchasesByItem'
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
            'A1:I1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range('A2:I3', 'Purchases by Item', heading_format)

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

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Item', cell_text_format)

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
            worksheet.write(row, column+4, 'Vendor', cell_text_format)

            worksheet.write(row, column+5, 'Ordered Qty', cell_number_format)
            worksheet.write(row, column+6, 'Received Qty', cell_number_format)
            worksheet.write(row, column+7, 'Billed Qty', cell_number_format)

            worksheet.write(row, column+8, 'Rate', cell_number_format)
            worksheet.write(row, column+9, 'Amount', cell_number_format)

        # Lines
        for main in lines(self.date_from, self.date_to, self.company_id.id, self.product_id.id, 'all'):
            # ------------------------------ Item ------------------------------

            for product in lines(self.date_from, self.date_to, self.company_id.id, self.product_id.id, 'yes'):

                if self.report_by == 'Summary':
                    row += 1
                    column = -1
                    worksheet.write(row, column+1, product['product_name'])
                    worksheet.write(
                        row, column+2, "{:,}".format(product['total_qty_ordered']), align_right)
                    worksheet.write(
                        row, column+3, "{:,}".format(product['total_qty_received']), align_right)
                    worksheet.write(
                        row, column+4, "{:,}".format(product['total_qty_billed']), align_right)
                    worksheet.write(
                        row, column+5, "{:,}".format(product['total_amount']), align_right_money)

                if self.report_by == 'Detail':
                    row += 2
                    column = -1
                    row_number = 'A%s:K%s' % (row, row)
                    worksheet.merge_range(
                        row_number, product['product_name'], cell_text_format)

                    # ------------------------------ Lines ------------------------------
                    for line in lines(self.date_from, self.date_to, self.company_id.id, product['product_id'], 'no'):
                        row += 1
                        column = -1

                        worksheet.write(row, column+1, '')
                        worksheet.write(
                            row, column+2, line['date_order'], date_format)
                        worksheet.write(row, column+3, line['order_no'])
                        worksheet.write(row, column+4, line['partner'])
                        worksheet.write(
                            row, column+5, "{:,}".format(line['qty_ordered']), align_right)
                        worksheet.write(
                            row, column+6, "{:,}".format(line['qty_received']), align_right)
                        worksheet.write(
                            row, column+7, "{:,}".format(line['qty_billed']), align_right)

                        worksheet.write(
                            row, column+8, line['price_total']/line['qty_ordered'], align_right)
                        worksheet.write(
                            row, column+9, "{:,}".format(line['price_total']), align_right_money)

                        # ---------------------------------------- END LINES ----------------------------------------

                    row += 2
                    column = -1
                    worksheet.write(row, column+1, 'TOTAL ' +
                                    product['product_name'], cell_text_format)
                    worksheet.write(row, column+2, '', cell_text_format)
                    worksheet.write(row, column+3, '', cell_text_format)
                    worksheet.write(row, column+4, '', cell_text_format)
                    worksheet.write(
                        row, column+5, "{:,}".format(product['total_qty_ordered']), align_right_total)
                    worksheet.write(
                        row, column+6, "{:,}".format(product['total_qty_received']), align_right_total)
                    worksheet.write(
                        row, column+7, "{:,}".format(product['total_qty_billed']), align_right_total)
                    worksheet.write(row, column+8, '')
                    worksheet.write(
                        row, column+9, "{:,}".format(product['total_amount']), align_right_money_total)

            # Main Totals
            row += 2
            column = -1
            worksheet.write(row, column+1, 'Total', cell_text_format)

            worksheet.write(
                row, column+2, "{:,}".format(main['total_qty_ordered_all']), align_right_total)
            worksheet.write(
                row, column+3, "{:,}".format(main['total_qty_received_all']), align_right_total)
            worksheet.write(
                row, column+4, "{:,}".format(main['total_qty_billed_all']), align_right_total)
            worksheet.write(
                row, column+5, "{:,}".format(main['total_amount_all']), align_right_money_total)

            if self.report_by == 'Detail':
                worksheet.write(row, column+2, '', cell_text_format)
                worksheet.write(row, column+3, '', cell_text_format)
                worksheet.write(row, column+4, '', cell_text_format)

                worksheet.write(
                    row, column+5, "{:,}".format(main['total_qty_ordered_all']), align_right_total)
                worksheet.write(
                    row, column+6, "{:,}".format(main['total_qty_received_all']), align_right_total)
                worksheet.write(
                    row, column+7, "{:,}".format(main['total_qty_billed_all']), align_right_total)
                worksheet.write(row, column+8, '', cell_number_format)
                worksheet.write(
                    row, column+9, "{:,}".format(main['total_amount_all']), align_right_money_total)

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


class PurchasesbyItemDetailReport(models.AbstractModel):
    _name = 'report.mgs_purchase.purchases_by_item_report'
    _description = 'Purchases by Item Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, product_id, is_group):  # , company_branch_ids
        full_move = []
        params = []

        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"

        if is_group == 'all':
            select = """select COALESCE(sum(pr.qty_ordered), 0) as total_qty_ordered_all, COALESCE(sum(pr.qty_received), 0) as total_qty_received_all,
            COALESCE(sum(pr.qty_billed), 0) as total_qty_billed_all, COALESCE(sum(pr.qty_to_be_billed), 0) as total_qty_to_be_billed_all,
            COALESCE(sum(amount_total), 0) as total_amount_all"""
            order = ""

        if is_group == 'yes':
            select = """select pt.name as product_name, pp.id as product_id,
            COALESCE(sum(pr.qty_ordered), 0) as total_qty_ordered, COALESCE(sum(pr.qty_received), 0) as total_qty_received,
            COALESCE(sum(pr.qty_billed), 0) as total_qty_billed, COALESCE(sum(pr.qty_to_be_billed), 0) as total_qty_to_be_billed,
            COALESCE(sum(amount_total), 0) as total_amount"""
            order = """
            group by pt.name, pp.id
            order by pt.name
            """

        if is_group == 'no':
            select = """
            select pr.date_order, po.name as order_no, rp.name as partner,
            pr.qty_ordered, pr.qty_received, pr.qty_billed, pr.qty_to_be_billed, amount_total as price_total, pr.state
            """

            order = """
            order by pr.date_order
            """
        from_where = """
        from purchase_report as pr
        left join purchase_order as po on pr.order_id=po.id
        left join res_partner as rp on pr.partner_id=rp.id
        left join product_product as pp on pr.product_id=pp.id
        left join product_template as pt on pr.product_tmpl_id=pt.id
        where pr.state in ('purchase', 'done')
        """

        if date_from:
            params.append(date_from)
            from_where += """ and pr.date_order >= %s"""

        if date_to:
            params.append(date_to)
            from_where += """ and pr.date_order <= %s"""

        if product_id:
            from_where += """ and pr.product_id = """ + str(product_id)

        if company_id:
            from_where += """ and pr.company_id = """ + str(company_id)

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
            'product_id': data['form']['product_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'lines': self._lines,
        }
