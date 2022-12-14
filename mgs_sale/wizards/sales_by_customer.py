from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError


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
