from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
