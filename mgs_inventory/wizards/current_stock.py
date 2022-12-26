from datetime import datetime, timedelta, date
from odoo import models, fields, api
import xlsxwriter
import base64
from io import BytesIO


class CurrentStock(models.TransientModel):
    _name = 'mgs_inventory.current_stock'
    _description = 'Current Stock'

    stock_location_ids = fields.Many2many(
        'stock.location', domain=[('usage', '=', 'internal')])
    date = fields.Datetime('Inventory at', default=fields.Datetime.now)
    # , domain = [('active', '=', True), ('type', '=', 'product')]
    product_id = fields.Many2one('product.product')
    categ_id = fields.Many2one('product.category')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get())
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            return {'domain': {'stock_location_ids': [('company_id', '=', self.company_id.id)]}}

    @api.onchange('categ_id')
    def onchange_categ_id(self):
        if self.categ_id:
            return {'domain': {'product_id': [('categ_id.id', '=', self.categ_id.id)]}}

        return {'domain': {'product_id': []}}

    def confirm(self):
        stock_location_ids = self.stock_location_ids.ids
        if not stock_location_ids:
            stock_location_ids = self.env['stock.location'].search(
                [('usage', '=', 'internal')]).ids

        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date': self.date,
                'product_id': self.product_id.id,
                'product_name': self.product_id.name,
                'categ_id': self.categ_id.id,
                'categ_name': self.categ_id.name,
                'stock_location_ids': stock_location_ids,
                'company_id': self.company_id.id,
                'company_name': self.company_id.name,

            },
        }

        return self.env.ref('mgs_inventory.action_current_stock').report_action(self, data=data)

    def export_to_excel(self):
        current_stock_report_obj = self.env['report.mgs_inventory.current_stock_report']
        sum_qty = current_stock_report_obj._sum_qty
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        # wbf, workbook = self.add_workbook_format(workbook)
        filename = 'Report'
        worksheet = workbook.add_worksheet(filename)
        # Formats
        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
        date_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
        cell_text_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12})
        cell_number_format = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12})
        align_right = workbook.add_format({'align': 'right'})
        align_right_total = workbook.add_format(
            {'align': 'right', 'bold': True})

        # Heading
        row = 1
        worksheet.merge_range(
            'A1:D1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range(
            'A2:D3', 'Quantity on Hand by Location', heading_format)
        row = 1
        worksheet.merge_range('A4:D4', self.date, date_heading_format)

        row += 1
        column = 0
        if self.product_id:
            worksheet.write(row, column+1, 'Product', cell_text_format)
            worksheet.write(row, column+2, self.product_id.name or '')

        if self.categ_id:
            worksheet.write(row, column+3, 'Category', cell_text_format)
            worksheet.write(row, column+4, self.categ_id.name or '')

        # Sub headers
        row += 1
        column = -1
        worksheet.write(row, column+1, 'Location', cell_text_format)
        worksheet.write(row, column+2, 'Item Code', cell_text_format)
        worksheet.write(row, column+3, 'Item Description', cell_text_format)
        worksheet.write(row, column+4, 'On Hand', cell_number_format)

        # data
        tot_qty_all = 0

        # get locations
        stock_location_ids = self.stock_location_ids.ids
        if not stock_location_ids:
            stock_location_ids = self.env['stock.location'].search(
                [('usage', '=', 'internal')])

        # get products
        domain = [('active', '=', True), ('type', '=', 'product')]
        if self.product_id:
            domain.append(('id', '=', self.product_id.id))

        if self.categ_id:
            domain.append(('categ_id', '=', self.categ_id.id))

        product_ids = self.env['product.product'].search(
            domain, order="default_code asc")

        for location in stock_location_ids:
            tot_qty = 0
            qty_by_location = sum_qty(
                self.date, self.categ_id.id, self.product_id.id, location.id, self.company_id.id)
            if not qty_by_location:
                continue

            row += 1
            column = -1
            worksheet.write(row, column+1, location.location_id.name +
                            '/' + location.name, cell_text_format)
            worksheet.write(row, column+2, '', cell_text_format)
            worksheet.write(row, column+3, '', cell_text_format)
            worksheet.write(row, column+4, '', cell_number_format)

            for product in product_ids:
                qty = sum_qty(self.date, self.categ_id.id,
                              product.id, location.id, self.company_id.id)
                if not qty:
                    continue

                row += 1
                column = -1
                tot_qty += qty
                worksheet.write(row, column+1, '')
                worksheet.write(row, column+2, product.default_code)
                worksheet.write(row, column+3, product.name)
                worksheet.write(row, column+4, qty, align_right)

            row += 1
            worksheet.write(row, column+1, 'Total ' + location.location_id.name +
                            '/' + location.name, cell_text_format)
            worksheet.write(row, column+2, '')
            worksheet.write(row, column+3, '')
            worksheet.write(
                row, column+4, "{:,}".format(tot_qty), align_right_total)
            tot_qty_all += tot_qty

        row += 3
        worksheet.write(row, column+1, 'Total', cell_text_format)
        worksheet.write(row, column+2, '')
        worksheet.write(row, column+3, '')
        worksheet.write(
            row, column+4, "{:,}".format(tot_qty_all), align_right_total)

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


class CurrentStockReport(models.AbstractModel):
    _name = 'report.mgs_inventory.current_stock_report'
    _description = 'Current Stock Report'

    @api.model
    def _sum_qty(self, date, categ_id, product_id, location_id, company_id):
        params = ['done']
        if date:
            params.append(date)

        query = """
        select sum(case
        when sld.id = """ + str(location_id) + """ then qty_done else -qty_done end) as Balance
        from stock_move_line  as sml
        left join stock_picking as sp on sml.picking_id=sp.id
        left join stock_location as sl on sml.location_id=sl.id
        left join stock_location as sld on sml.location_dest_id=sld.id
        left join stock_move as sm on sml.move_id=sm.id
        left join res_partner as rp on sm.partner_id = rp.id
        left join product_product as pp on sml.product_id = pp.id
        left join product_template as pt on pt.id = pp.product_tmpl_id
        where not sl.id = sld.id and sml.state = %s
        """

        if date:
            query += """ and sml.date < %s"""

        if location_id:
            query += """ and (sml.location_id = """ + str(location_id) + \
                """ or sml.location_dest_id = """ + str(location_id) + """)"""

        if categ_id:
            query += """ and pt.categ_id = """ + str(categ_id)

        if product_id:
            query += """ and pp.id = """ + str(product_id)

        if company_id:
            query += """ and sm.company_id = """ + str(company_id)

        self.env.cr.execute(query, tuple(params))

        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    @api.model
    # def _get_report_values(self, docids, data=None):
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        date = data['form']['date']
        product_id = data['form']['product_id']
        product_name = data['form']['product_name']
        categ_id = data['form']['categ_id']
        categ_name = data['form']['categ_name']
        company_id = data['form']['company_id']
        company_name = data['form']['company_name']
        stock_location_ids = data['form']['stock_location_ids']

        # 'location_ids' = self.env['stock.location'].search([('id', 'in', stock_location_ids)])
        domain = [('active', '=', True), ('type', '=', 'product')]

        if product_id:
            domain.append(('id', '=', product_id))

        if categ_id:
            domain.append(('categ_id', '=', categ_id))

        product_ids = self.env['product.product'].search(
            domain, order="default_code asc")

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'date': date,
            'product_id': product_id,
            'product_name': product_name,
            'categ_id': categ_id,
            'categ_name': categ_name,
            'company_id': self.env['res.company'].search([('id', '=', company_id)]),
            'company_name': company_name,
            'stock_location_ids': stock_location_ids,
            'sum_qty': self._sum_qty,
            'location_ids': self.env['stock.location'].search([('id', 'in', stock_location_ids), ('company_id', '=', company_id)]),
            'product_ids': product_ids
        }
