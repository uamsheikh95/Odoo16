from odoo import models, fields, api
from datetime import datetime, timedelta, date
import xlsxwriter
import base64
from io import BytesIO


class ProductMovesHistory(models.TransientModel):
    _name = 'mgs_inventory.pr_moves_history'
    _description = 'Product Moves History'
    stock_location_ids = fields.Many2many(
        'stock.location', domain=[('usage', '=', 'internal')], required=True)
    partner_id = fields.Many2one('res.partner', string="Partner")
    product_id = fields.Many2one('product.product')
    date_from = fields.Datetime('From', default=datetime.today().replace(
        day=1, hour=00, minute=00, second=00))
    date_to = fields.Datetime('To', default=fields.Datetime.now)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self:
                                 self.env['res.company']._company_default_get('mgs_inventory.pr_moves_history'))
    view = fields.Selection([('all', 'All Products'), ('active', 'Active Products'), (
        'inactive', 'Inactive Products')], string='View', default='all')
    include_reserved = fields.Boolean(default=False, string="Include Reserved")
    show_reserved_only = fields.Boolean(
        default=False, string="Show Reserved Only")
    order_id = fields.Many2one('sale.order', string="Order")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.onchange('warehouse_id')
    def onchange_source_warehouse(self):
        if self.warehouse_id:
            self.stock_location_ids = self.env['stock.location'].search(
                [('location_id', 'child_of', self.warehouse_id.view_location_id.id), ('usage', '=', 'internal')])

    def confirm(self):
        """Call when button 'Get Rep=t' clicked.
        """
        print('=================================')
        print(self.stock_location_ids.ids)
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'product_id': self.product_id.id,
                'stock_location_ids': self.stock_location_ids.ids,
                'partner_id': self.partner_id.id,
                'product_name': self.product_id.name,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'company_name': self.company_id.name,
                # 'company_branch_id': self.company_branch_id.id,
                # 'company_branch_name': self.company_branch_id.name,
                'include_reserved': self.include_reserved,
                'show_reserved_only': self.show_reserved_only,
                'order_id': self.order_id.name,
                'view': self.view,
            },
        }

        return self.env.ref('mgs_inventory.action_report_product_moves').report_action(self, data=data)

    def export_to_excel(self):
        pr_moves_history_report_obj = self.env['report.mgs_inventory.pr_moves_history_report']
        lines = pr_moves_history_report_obj._lines
        open_balance = pr_moves_history_report_obj._sum_open_balance
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        # wbf, workbook = self.add_workbook_format(workbook)
        filename = 'ProductMovesHistoryReport'
        worksheet = workbook.add_worksheet(filename)
        # Formats
        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
        date_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
        date_format = workbook.add_format({'num_format': 'd-m-yyyy'})
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
            'A1:I1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range(
            'A2:I3', 'Product Moves History', heading_format)

        row += 1
        column = -1
        if self.date_from:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'From', date_heading_format)
            worksheet.write(row, column+2, self.date_from or '', date_format)

        if self.date_to:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'To', date_heading_format)
            worksheet.write(row, column+2, self.date_to or '', date_format)

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

        if self.order_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Order', cell_text_format)
            worksheet.write(row, column+2, self.order_id.name or '')

        # Sub headers
        row += 1
        column = -1
        worksheet.write(row, column+1, 'Product', cell_text_format)
        worksheet.write(row, column+2, 'Date', cell_text_format)
        worksheet.write(row, column+3, 'From > To', cell_text_format)
        worksheet.write(row, column+4, 'Source', cell_text_format)
        worksheet.write(row, column+5, 'Partner', cell_text_format)
        worksheet.write(row, column+6, 'Qty in', cell_number_format)
        worksheet.write(row, column+7, 'Qty out', cell_number_format)

        if self.include_reserved:
            worksheet.write(row, column+8, 'Reserved', cell_number_format)
            worksheet.write(row, column+9, 'Balance', cell_number_format)
        else:
            worksheet.write(row, column+8, 'Balance', cell_number_format)

        for main in lines(self.product_id.id, self.date_from, self.date_to, self.stock_location_ids.ids, self.partner_id.id, self.include_reserved, self.show_reserved_only, self.order_id.id, 'all'):
            total_balance_all = 0
            total_reserved_all = 0
            for product in lines(self.product_id.id, self.date_from, self.date_to, self.stock_location_ids.ids, self.partner_id.id, self.include_reserved, self.show_reserved_only, self.order_id.id, 'yes'):
                total_balance = 0
                total_reserved = 0
                balance = open_balance(
                    product['product_id'], self.date_from, self.stock_location_ids.ids, self.partner_id.id)
                total_qty_in = 0
                total_qty_out = 0
                row += 1
                column = -1
                worksheet.write(
                    row, column+1, product['group']['en_US'], cell_text_format)

                if self.include_reserved:
                    worksheet.write(
                        row, column+8, 'Qty Balance Forward', cell_text_format)
                    worksheet.write(
                        row, column+9, '{:,.2f}'.format(balance), cell_number_format)
                else:
                    worksheet.write(
                        row, column+7, 'Qty Balance Forward', cell_text_format)
                    worksheet.write(
                        row, column+8, '{:,.2f}'.format(balance), cell_number_format)

                for line in lines(product['product_id'], self.date_from, self.date_to, self.stock_location_ids.ids, self.partner_id.id, self.include_reserved, self.show_reserved_only, self.order_id.id, 'no'):
                    row += 1
                    column = -1

                    worksheet.write(row, column+2, line['date'], date_format)
                    worksheet.write(row, column+3, '%s > %s' %
                                    (line['location_id'], line['location_dest_id']))
                    worksheet.write(row, column+4, '%s | %s' %
                                    (line['picking_id'], line['origin']))
                    worksheet.write(row, column+5, line['partner_id'])

                    qty_in = line['qty_done'] if line['location_id_id'] not in self.stock_location_ids.ids else 0
                    qty_out = line['qty_done'] if line['location_id_id'] in self.stock_location_ids.ids else 0
                    worksheet.write(
                        row, column+6, '{:,.2f}'.format(qty_in), align_right)
                    worksheet.write(
                        row, column+7, '{:,.2f}'.format(qty_out), align_right)

                    balance += qty_in - qty_out
                    total_qty_in + qty_in
                    total_qty_out + qty_out

                    if self.include_reserved:
                        worksheet.write(
                            row, column+8, '{:,.2f}'.format(line['reserved_qty']), align_right)
                        worksheet.write(
                            row, column+9, '{:,.2f}'.format(balance), align_right)
                    else:
                        worksheet.write(
                            row, column+8, '{:,.2f}'.format(balance), align_right)

                row += 1
                column = -1
                worksheet.write(row, column+1, 'Total ' +
                                product['group']['en_US'], cell_text_format)

                worksheet.write(
                    row, column+6, '{:,.2f}'.format(product['total_product_in']), cell_number_format)
                worksheet.write(
                    row, column+7, '{:,.2f}'.format(product['total_product_out']), cell_number_format)

                if self.include_reserved:
                    worksheet.write(row, column+7, '', cell_text_format)
                    worksheet.write(
                        row, column+8, '{:,.2f}'.format(balance), cell_number_format)
                else:
                    worksheet.write(row, column+7, '', cell_text_format)
                    worksheet.write(
                        row, column+8, '{:,.2f}'.format(balance), cell_number_format)

                total_balance_all += balance

            row += 1
            column = -1
            worksheet.write(row, column+1, 'Total', cell_text_format)

            worksheet.write(
                row, column+6, '{:,.2f}'.format(main['total_product_in_all']), cell_number_format)
            worksheet.write(
                row, column+7, '{:,.2f}'.format(main['total_product_out_all']), cell_number_format)

            if self.include_reserved:
                worksheet.write(row, column+7, '', cell_text_format)
                worksheet.write(
                    row, column+8, '{:,.2f}'.format(total_balance_all), cell_number_format)
            else:
                worksheet.write(row, column+7, '', cell_text_format)
                worksheet.write(
                    row, column+8, '{:,.2f}'.format(total_balance_all), cell_number_format)

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


class ProductMovesHistoryReport(models.AbstractModel):
    _name = 'report.mgs_inventory.pr_moves_history_report'
    _description = 'Product Moves History Report'

    def _lines(self, product_id, date_from, date_to, stock_location_ids, partner_id, include_reserved, show_reserved_only, order_id, is_group):
        full_move = []
        if order_id:
            params = [date_from, date_to, order_id]  # , company_branch_id
        else:
            params = [date_from, date_to]  # , company_branch_id

        states = """('done')"""
        if include_reserved:
            states = """('done','assigned')"""
        if show_reserved_only:
            states = """('assigned')"""
        cases_query = """
        case
            when sld.id in ( """ + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end as ProductIn,
        case
            when sl.id in (""" + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end as ProductOut, 0 as Balance
        """
        # +++++++++++++++++++++++
        if is_group == 'all':
            select_query = """select
            COALESCE(sum(case when sld.id in ( """ + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end), 0) as total_product_in_all,
            COALESCE(sum(case when sl.id in (""" + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end), 0) as total_product_out_all
            """

            order_by = ""

        if is_group == 'yes':
            select_query = """select pt.name as group, pp.id as product_id,
            COALESCE(sum(case when sld.id in ( """ + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end), 0) as total_product_in,
            COALESCE(sum(case when sl.id in (""" + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end), 0) as total_product_out
            """

            order_by = """
            group by pt.name, pp.id
            order by 1"""

        if is_group == 'no':
            select_query = """
            select sml.date, sp.origin,sp.name as picking_id,sml.product_id, sml.qty_done,sml.state as state,sml.reserved_qty as reserved_qty,rp.name as partner_id, pp.id as product_id,
            sl.name as location_id,sl.id as location_id_id, sld.id as location_dest_id_id, sld.name as location_dest_id, sld.usage as location_usage, sml.state, sl.usage usage, sld.usage usaged, COALESCE(sm.price_unit, 0) as price_unit,
            """+cases_query

            order_by = """ order by 1"""

        from_where = """
        from stock_move_line as sml
        left join stock_location as sl on sml.location_id=sl.id
        left join stock_picking as sp on sml.picking_id=sp.id
        left join stock_location as sld on sml.location_dest_id=sld.id
        left join stock_move as sm on sml.move_id=sm.id
        left join res_partner as rp on sm.partner_id=rp.id
        left join product_product as pp on sml.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        where not (sl.id = sld.id) and sml.state in """ + states + """
        and sml.date between %s and %s and pt.type = 'product'
        """

        if len(stock_location_ids) > 0:
            from_where += """ and (sl.id in (""" + ','.join(map(str, stock_location_ids)) + \
                """) or sld.id in (""" + ','.join(map(str,
                                                      stock_location_ids)) + """))"""

        if partner_id:
            from_where += """ and rp.id = """ + str(partner_id)

        if product_id:
            from_where += """ and sml.product_id = """ + str(product_id)

        if order_id:
            from_where += """ and sp.origin = %s"""

        # if  company_branch_id:
        #     query += """ and br.id = """ + str(company_branch_id)
        query = select_query + from_where + order_by

        # and company_branch_id = %s
        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        '''
        for r in res:
            if r['stored_origin'] and 'PO' in r['stored_origin']:
                r['partner_id'] = self.env['purchase.order'].search([('name', '=', r['stored_origin'])]).partner_id.name
            elif r['stored_origin'] and 'SO' in r['stored_origin']:
                r['partner_id'] = self.env['sale.order'].search([('name', '=', r['stored_origin'])]).partner_id.name
            full_move.append(r)
        '''
        return res

    # , company_branch_id
    def _sum_open_balance(self, product_id, date_from, stock_location_ids, partner_id):
        params = [product_id, date_from]  # , company_branch_id
        # pre_query= """
        # select sum(case
        # when sld.id in (
        # """ + ','.join(map(str, stock_location_ids)) +""" ) then qty_done else -qty_done end) as Balance """
        pre_query = """
        select
        COALESCE(sum(case when sld.id in ( """ + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end), 0) as total_product_in,
        COALESCE(sum(case when sl.id in (""" + ','.join(map(str, stock_location_ids)) + """) then qty_done else 0 end), 0) as total_product_out"""
        query = """
            from stock_move_line  as sml
            left join stock_picking as sp on sml.picking_id=sp.id
            left join stock_location as sl on sml.location_id=sl.id
            left join stock_location as sld on sml.location_dest_id=sld.id
            left join stock_move as sm on sml.move_id=sm.id
            left join res_partner as rp on sm.partner_id = rp.id
            where sml.product_id = %s and sml.state = 'done'
            and sml.date < %s
        """

        if len(stock_location_ids) > 0:
            query += """ and (sml.location_id in (""" + ','.join(map(str, stock_location_ids)) + \
                """) or sml.location_dest_id in (""" + ','.join(
                    map(str, stock_location_ids)) + """))"""

        if partner_id:
            query += """ and rp.id = """ + str(partner_id)

        query = pre_query + query

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        res = res[0]['total_product_in'] - res[0]['total_product_out']
        return res

    # def _get_item_avg_cost(self, picking_no, product_id):
    #     picking_id = self.env['stock.picking'].search(
    #         [('name', '=', picking_no)], limit=1)

    #     scraps = self.env['stock.scrap'].search(
    #         [('picking_id', '=', picking_id.id)])
    #     domain = [('id', 'in', (picking_id.move_lines + scraps.move_id)
    #                .stock_valuation_layer_ids.ids), ('product_id', '=', product_id)]

    #     qty = 0
    #     value = 0
    #     for valuation in self.env['stock.valuation.layer'].search(domain):
    #         qty += valuation.quantity
    #         value += valuation.value

    #     result = value / qty if qty != 0 else 0
    #     if qty < 0 or value < 0 and qty != 0:
    #         result = (value * -1) / (qty * -1) or 0
    #     return result

    @api.model
    # def _get_report_values(self, docids, data=None):
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        product_id = data['form']['product_id']
        product_name = data['form']['product_name']
        company_id = data['form']['company_id']
        company_name = data['form']['company_name']
        stock_location_ids = data['form']['stock_location_ids']
        partner_id = data['form']['partner_id']
        include_reserved = data['form']['include_reserved']
        show_reserved_only = data['form']['show_reserved_only']
        order_id = data['form']['order_id']
        view = data['form']['view']

        product_list = []
        #
        # if product_id:
        #     for r in self.env['stock.move'].search([('date', '>=', date_from), ('date', '<=', date_to), ('product_id', '=', product_id)], order="product_id asc"):
        #         if r.product_id not in product_list:
        #             product_list.append(r.product_id)
        # else:
        #     if view == 'all':
        #         for r in self.env['stock.move'].search([('date', '>=', date_from), ('date', '<=', date_to)], order="product_id asc"):
        #             if r.product_id not in product_list:
        #                 product_list.append(r.product_id)
        #     elif view == 'active':
        #         for r in self.env['stock.move'].search([('date', '>=', date_from), ('date', '<=', date_to)], order="product_id asc"):
        #             if r.product_id not in product_list and r.product_id.active == True:
        #                 product_list.append(r.product_id)
        #
        #     elif view == 'inactive':
        #         for r in self.env['stock.move'].search([('date', '>=', date_from), ('date', '<=', date_to)], order="product_id asc"):
        #             if r.product_id not in product_list and r.product_id.active == False:
        #                 product_list.append(r.product_id)

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'date_from': date_from,
            'date_to': date_to,
            'product_id': product_id,
            'product_name': product_name,
            'company_id': self.env.company,
            'company_name': company_name,
            # 'company_branch_id': company_branch_id,
            # 'company_branch_name': company_branch_name,
            'include_reserved': include_reserved,
            'show_reserved_only': show_reserved_only,
            'order_id': order_id,
            'partner_id': partner_id,
            'stock_location_ids': stock_location_ids,
            'lines': self._lines,
            'open_balance': self._sum_open_balance,
            'product_list': product_list,
            # 'get_item_avg_cost': self._get_item_avg_cost
        }
