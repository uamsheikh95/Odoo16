from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
from itertools import groupby
from operator import itemgetter
from itertools import groupby
import xlsxwriter
import base64
from io import BytesIO


class MgsReserveditems(models.TransientModel):
    _name = 'mgs_inventory.reserved_items'
    _description = 'Mgs Reserved items'

    stock_location_ids = fields.Many2many(
        'stock.location', domain=[('usage', '=', 'internal')], required=True)
    partner_id = fields.Many2one('res.partner', string="Partner")
    product_id = fields.Many2one('product.product')
    date = fields.Date('At', default=fields.Datetime.now)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    order_id = fields.Many2one('sale.order', string="Order")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    report_by = fields.Selection([('Summary', 'Summary'), ('Detail', 'Detail')],
                                 string='Report by', default='Detail', required=True)
    group_by = fields.Selection([('Customer', 'Customer'), ('Item', 'Item')],
                                string='Report by', default='Customer', required=True)
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.onchange('warehouse_id')
    def onchange_source_warehouse(self):
        if self.warehouse_id:
            self.stock_location_ids = self.env['stock.location'].search(
                [('location_id', 'child_of', self.warehouse_id.view_location_id.id), ('usage', '=', 'internal')])

    def confirm(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'product_id': [self.product_id.id, self.product_id.name],
                'stock_location_ids': self.stock_location_ids.ids,
                'date': self.date,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
                'group_by': self.group_by,
                'order_id': self.order_id.name,
            },
        }

        return self.env.ref('mgs_inventory.action_reserved_items_report').report_action(self, data=data)

    def export_to_excel(self):
        reserved_items_report_obj = self.env['report.mgs_inventory.reserved_items_report']
        lines = reserved_items_report_obj._lines
        open_balance = reserved_items_report_obj._sum_open_balance

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
        date_format = workbook.add_format({'num_format': 'd-m-yyyy'})
        cell_number_format = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12})
        align_right = workbook.add_format({'align': 'right'})
        align_right_total = workbook.add_format(
            {'align': 'right', 'bold': True})

        # Heading
        row = 1
        worksheet.merge_range(
            'A1:F1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range(
            'A2:F3', 'Reserved by %s %s' % (self.group_by, self.report_by), heading_format)
        row += 1
        worksheet.merge_range(
            'A4:F4', 'At %s' % self.date)

        if self.product_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Product', cell_text_format)
            worksheet.write(row, column+2, self.product_id.name or '')

        if self.partner_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Partner', cell_text_format)
            worksheet.write(row, column+2, self.partner_id.name or '')

        # Sub headers
        row += 1
        column = -1
        worksheet.write(row, column+1, self.group_by, cell_text_format)
        worksheet.write(row, column+2, 'Date', cell_text_format)
        worksheet.write(row, column+3, 'Ref#', cell_text_format)
        group = 'Product' if self.group_by == 'Customer' else 'Item'
        worksheet.write(row, column+4, group, cell_text_format)
        worksheet.write(row, column+5, 'Reserved', cell_number_format)
        worksheet.write(row, column+6, 'Balance', cell_number_format)

        total_reserved_all = 0
        total_balance_all = 0
        # product_id, date_from, date_to, stock_location_ids, partner_id, group_by, order_id, company_id
        for group in lines(self.product_id.id, self.date, self.stock_location_ids.ids, self.partner_id.id, self.group_by, self.order_id.name, self.company_id.id):
            if self.report_by == 'Detail':
                row += 1
                column = -1
                balance = 0
                if self.group_by == 'Item' and self.date_from:
                    balance = open_balance(
                        group['name'][0], self.date_from, self.stock_location_ids.ids, self.partner_id.id)
                elif self.group_by == 'Item' and self.date_from:
                    balance = open_balance(
                        self.product_id.id, self.date_from, self.stock_location_ids.ids, self.partner_id.id)

                product_customer = group['name'][1]['en_US'] if self.group_by == 'Item' else group['name'][1]
                worksheet.write(
                    row, column+1, product_customer, cell_text_format)
                worksheet.write(
                    row, column+5, 'Initital Balance', cell_text_format)
                worksheet.write(row, column+6, int(balance),
                                cell_number_format)

            for line in group['lines']:
                row += 1
                column = -1

                balance += line['reserved_qty']

                if self.report_by == 'Detail':
                    worksheet.write(row, column+2, line['date'], date_format)
                    worksheet.write(row, column+3, '%s | %s' %
                                    (line['picking_id'], line['origin']), date_format)
                    product_customer = line['partner_name'] if line[
                        'partner_name'] and self.group_by == 'Customer' else line['product_name']
                    worksheet.write(row, column+4, product_customer)
                    worksheet.write(
                        row, column+5, int(line['reserved_qty']), align_right)
                    worksheet.write(row, column+6, int(balance), align_right)

            row += 1
            column = -1
            product_customer = group['name'][1] if self.group_by == 'Customer' else group['name'][1]['en_US']
            total = '%s %s' % (
                'Total ', product_customer) if self.report_by == 'Detail' else product_customer
            worksheet.write(row, column+1, total, cell_text_format)
            worksheet.write(row, column+6, int(balance), cell_number_format)
            total_balance_all += balance

        row += 1
        column = -1
        worksheet.write(row, column+1, 'Total', cell_text_format)
        worksheet.write(row, column+6, int(total_balance_all),
                        cell_number_format)

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


class MgsReserveditemsReport(models.AbstractModel):
    _name = 'report.mgs_inventory.reserved_items_report'
    _description = 'Mgs Reserved items Report'

    @api.model
    def _lines(self, product_id, date, stock_location_ids, partner_id, group_by, order_id, company_id):
        lines = []
        params = []

        t_date = str(date) + " 23:59:59"

        # cases_query = """
        # case
        #     when sld.id in ( """ + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end as ProductIn,
        # case
        #     when sl.id in (""" + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end as ProductOut, 0 as Balance"""

        # params.append(cases_query)

        query = """
        select sml.date, sp.origin,sp.name as picking_id, sml.qty_done,sml.state as state,
        sml.reserved_qty as reserved_qty, sm.partner_id as partner_id, rp.name as partner_name,
        sml.product_id as product_id, pt.name as product_name, sml.location_id as location_id, 
        sl.name as location_name, sml.location_dest_id as location_dest_id, sld.name as location_dest_name,
        sld.usage as location_usage,  sml.state, sl.usage usage, sld.usage usaged, COALESCE(sm.price_unit, 0) as price_unit

        from stock_move_line as sml
        left join stock_location as sl on sml.location_id=sl.id
        left join stock_picking as sp on sml.picking_id=sp.id
        left join stock_location as sld on sml.location_dest_id=sld.id
        left join stock_move as sm on sml.move_id=sm.id
        left join res_partner as rp on sm.partner_id=rp.id
        left join product_product as pp on sml.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        where not (sl.id = sld.id) and sml.state = 'assigned'
        and pt.type = 'product'
        """

        if len(stock_location_ids) > 0:
            query += """ and (sl.id in (""" + ','.join(map(str, stock_location_ids)) + \
                """) or sld.id in (""" + ','.join(map(str,
                                                      stock_location_ids)) + """))"""
        if date:
            params.append(date)
            query += """ and sml.date >= %s"""

        if partner_id:
            params.append(partner_id)
            query += " and sm.partner_id = %s"

        if product_id:
            params.append(product_id)
            query += " and sml.product_id = %s"

        if order_id:
            params.append(order_id)
            query += " and sp.origin = %s"

        if company_id:
            params.append(company_id)
            query += " and sml.company_id = %s"

        query += "order by date asc"

        self.env.cr.execute(query, tuple(params))

        key = itemgetter('product_id', 'product_name') if group_by == 'Product' else itemgetter(
            'partner_id', 'partner_name')
        res = sorted(self.env.cr.dictfetchall(), key=key)

        for key, value in groupby(res, key):
            # lines.append({'Name': key, 'Lines': list(value), 'Total': sum(item['Total'] for item in value)})
            # print(key)
            sub_lines = []
            total_reserved = 0

            for k in value:
                sub_lines.append(k)
                total_reserved += k['reserved_qty']

            lines.append({'name': key, 'lines': sub_lines,
                         'total_reserved': total_reserved})
        return lines

    def _sum_open_balance(self, product_id, date_from, stock_location_ids, partner_id):
        params = []  # , company_branch_id
        # pre_query= """
        # select sum(case
        # when sld.id in (
        # """ + ','.join(map(str, stock_location_ids)) +""" ) then qty_done else -qty_done end) as Balance """
        query = """
        select
        COALESCE(sum(sml.reserved_qty), 0) as result 
        from stock_move_line  as sml
        left join stock_picking as sp on sml.picking_id=sp.id
        left join stock_location as sl on sml.location_id=sl.id
        left join stock_location as sld on sml.location_dest_id=sld.id
        left join stock_move as sm on sml.move_id=sm.id
        left join res_partner as rp on sm.partner_id = rp.id
        where sml.state = 'assigned'
        """

        if len(stock_location_ids) > 0:
            query += """ and (sml.location_id in (""" + ','.join(map(str, stock_location_ids)) + \
                """) or sml.location_dest_id in (""" + ','.join(
                    map(str, stock_location_ids)) + """))"""

        if date_from:
            params.append(date_from)
            query += " and sml.date < %s"

        if product_id:
            params.append(product_id)
            query += " and sml.product_id = %s"

        if partner_id:
            params.append(partner_id)
            query += " and rp.id = %s"

        self.env.cr.execute(query, tuple(params))
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    def _get_item_avg_cost(self, picking_no, product_id):
        picking_id = self.env['stock.picking'].search(
            [('name', '=', picking_no)], limit=1)

        scraps = self.env['stock.scrap'].search(
            [('picking_id', '=', picking_id.id)])
        domain = [('id', 'in', (picking_id.move_lines + scraps.move_id)
                   .stock_valuation_layer_ids.ids), ('product_id', '=', product_id)]

        qty = 0
        value = 0
        for valuation in self.env['stock.valuation.layer'].search(domain):
            qty += valuation.quantity
            value += valuation.value

        result = value / qty if qty != 0 else 0
        if qty < 0 or value < 0 and qty != 0:
            result = (value * -1) / (qty * -1) or 0
        return result

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
            'product_id': data['form']['product_id'],
            'stock_location_ids': data['form']['stock_location_ids'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'order_id': data['form']['order_id'],
            'report_by': data['form']['report_by'],
            'group_by': data['form']['group_by'],
            'lines': self._lines,
            'open_balance': self._sum_open_balance,
            'get_item_avg_cost': self._get_item_avg_cost
        }
