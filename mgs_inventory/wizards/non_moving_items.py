from calendar import month
from odoo import models, fields, api


class NonMovingItems(models.TransientModel):
    _name = 'mgs_inventory.non_moving_items'
    _description = 'Non Moving Items'

    from_date = fields.Date(
        'From Date', default=lambda self: fields.Date.today().replace(day=1), required=True)
    # , default=lambda self: fields.Date.today().replace(month=12, day=31)
    to_date = fields.Date('To Date', required=True,
                          default=lambda self: fields.Date.today())
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    stock_location_ids = fields.Many2many(
        'stock.location', domain=[('usage', '=', 'internal')], required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id, required=True)

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
                'warehouse_id': [self.warehouse_id.id, self.warehouse_id.name],
                'company_id': [self.company_id.id, self.company_id.name],
                'stock_location_ids': self.stock_location_ids.ids,
                'from_date': self.from_date,
                'to_date': self.to_date,
            },
        }

        return self.env.ref('mgs_inventory.action_report_non_moving_items').report_action(self, data=data)


class NonMovingItemsReport(models.AbstractModel):
    _name = 'report.mgs_inventory.non_moving_items_report'
    _description = 'Non Moving Items Report'

    def _lines(self, from_date, to_date, stock_location_ids, company_id):
        #     sub_query = """SELECT sml.product_id
        #   FROM stock_move_line sml
        #   LEFT JOIN stock_location as sl ON sml.location_id=sl.id
        #   LEFT JOIN stock_location as sld ON sml.location_dest_id=sld.id
        #   LEFT JOIN product_product as pp ON sml.product_id = pp.id
        #   LEFT JOIN product_template as pt ON pt.id = pp.product_tmpl_id
        #   WHERE sld.usage = 'customer' and sml.date between '2022-9-1' and '2022-12-1'
        #   """

        # if from_date:
        #     sub_query += " AND sml.date >= %s" % from_date

        # if to_date:
        #     sub_query += " AND sml.date <= %s" % to_date

        # if len(stock_location_ids) > 0:
        #     sub_query += " AND (sl.id in (" + ','.join(map(str, stock_location_ids)) + \
        #         ") or sld.id in (" + \
        #         ','.join(map(str, stock_location_ids)) + "))"

        # if company_id:
        #     sub_query += " AND sml.company_id = %s" % company_id

        params = []

        query = """
        select pt.name product_name, sum(case
        when sld.id in (""" + ','.join(map(str, stock_location_ids)) + """) then qty_done else -qty_done end) as total_qty
        from stock_move_line  as sml
        left join stock_picking as sp on sml.picking_id=sp.id
        left join stock_location as sl on sml.location_id=sl.id
        left join stock_location as sld on sml.location_dest_id=sld.id
        left join stock_move as sm on sml.move_id=sm.id
        left join res_partner as rp on sm.partner_id = rp.id
        left join product_product as pp on sml.product_id = pp.id
        left join product_template as pt on pt.id = pp.product_tmpl_id
        where sml.state = 'done' and pp.id not in (
            SELECT sml.product_id
            FROM stock_move_line sml
            LEFT JOIN stock_location as sl ON sml.location_id=sl.id
            LEFT JOIN stock_location as sld ON sml.location_dest_id=sld.id
            LEFT JOIN product_product as pp ON sml.product_id = pp.id
            LEFT JOIN product_template as pt ON pt.id = pp.product_tmpl_id
            WHERE sld.usage = 'customer'
        """

        if from_date:
            params.append(from_date)
            query += " AND sml.date >= %s"

        if to_date:
            params.append(to_date)
            query += " AND sml.date <= %s"

        if len(stock_location_ids) > 0:
            query += " AND (sl.id in (" + ','.join(map(str, stock_location_ids)) + \
                ") or sld.id in (" + \
                ','.join(map(str, stock_location_ids)) + "))"

        if company_id:
            params.append(company_id)
            query += " AND sml.company_id = %s"

        query += """) and (sl.id in (""" + ','.join(map(str, stock_location_ids)) + """) or sld.id in (""" + ','.join(map(str, stock_location_ids)) + """))
        and not (sl.id = sld.id)
        group by pt.name
        order by pt.name
        """
        self.env.cr.execute(query, tuple(params))  # , tuple(params)
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
            'from_date': data['form']['from_date'],
            'to_date': data['form']['to_date'],
            'stock_location_ids': data['form']['stock_location_ids'],
            'warehouse_id': data['form']['warehouse_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'lines': self._lines
        }
