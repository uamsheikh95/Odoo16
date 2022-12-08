from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SalesbyItemDetail(models.TransientModel):
    _name = 'mgs_sale.sales_by_item'
    _description = 'Sales by Item'

    product_id = fields.Many2one('product.product', string="Product")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    report_by = fields.Selection(
        [('Summary', 'Summary'), ('Detail', 'Detail')], string='Report Type', default='Detail')
    user_id = fields.Many2one('res.users', string='Salesperson')

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
                'user_id': [self.user_id.id, self.user_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
            },
        }

        return self.env.ref('mgs_sale.action_sales_by_item').report_action(self, data=data)


class SalesbyItemDetailReport(models.AbstractModel):
    _name = 'report.mgs_sale.sales_by_item_report'
    _description = 'Sales by Item Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, product_id, user_id, is_group):  # , company_branch_ids
        full_move = []
        params = []

        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"

        if is_group == 'all':
            select = """select
            COALESCE(sum(sr.product_uom_qty), 0) as total_qty_ordered_all, COALESCE(sum(sr.qty_delivered), 0) as total_qty_delivered_all,
            COALESCE(sum(sr.qty_invoiced), 0) as total_qty_invoiced_all, COALESCE(sum(sr.qty_to_invoice), 0) as total_qty_to_invoice_all,
            COALESCE(sum(sr.price_total), 0) as total_amount_all, COALESCE(sum(sr.price_total), 0) as total_amount_all,
            COALESCE(sum(sr.price_total-sr.margin), 0) as total_cost_all, COALESCE(sum(sr.margin), 0) as total_margin_all"""
            order = ""

        if is_group == 'yes':
            select = """select pt.name as product_name, pp.id as product_id,
            COALESCE(sum(sr.product_uom_qty), 0) as total_qty_ordered, COALESCE(sum(sr.qty_delivered), 0) as total_qty_delivered,
            COALESCE(sum(sr.qty_invoiced), 0) as total_qty_invoiced, COALESCE(sum(sr.qty_to_invoice), 0) as total_qty_to_invoice,
            COALESCE(sum(sr.price_total), 0) as total_amount, COALESCE(sum(sr.price_total-sr.margin), 0) as total_cost,
            COALESCE(sum(sr.margin), 0) as total_margin"""
            order = """
            group by pt.name, pp.id
            order by pt.name
            """

        if is_group == 'no':
            select = """
            select sr.date, sr.name as order_no, rp.name as partner,
            COALESCE(sr.product_uom_qty, 0), COALESCE(sr.qty_delivered, 0), COALESCE(sr.qty_invoiced, 0), COALESCE(sr.qty_to_invoice, 0), COALESCE(sr.price_total, 0),
            sr.state, COALESCE(sr.price_total-sr.margin, 0) as cost, COALESCE(sr.margin, 0)
            """

            order = """
            order by sr.date
            """
        from_where = """
        from sale_report as sr
        left join res_partner as rp on sr.partner_id=rp.id
        left join product_product as pp on sr.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        where sr.state in ('sale', 'done', 'paid', 'pos_done', 'invoiced')
        """

        if date_from:
            params.append(f_date)
            from_where += """ and sr.date >= %s"""

        if date_to:
            params.append(t_date)
            from_where += """ and sr.date <= %s"""

        if product_id:
            from_where += """ and sr.product_id = """ + str(product_id)

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
            'product_id': data['form']['product_id'],
            'user_id': data['form']['user_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'lines': self._lines,
        }
