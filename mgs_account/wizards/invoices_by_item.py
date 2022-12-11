from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InvoicesbyItem(models.TransientModel):
    _name = 'mgs_account.invoices_by_item'
    _description = 'Invoices by Item'

    product_id = fields.Many2one('product.product', string="Product")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    invoices_bills = fields.Selection([('Invoices', 'Invoices'), (
        'Bills', 'Bills')], string='Invoices/Bills', default='Invoices', required=True)
    report_by = fields.Selection([('Summary', 'Summary'), ('Detail', 'Detail')],
                                 string='Report Type', default='Detail', required=True)

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
                'invoices_bills': self.invoices_bills,
            },
        }

        return self.env.ref('mgs_account.action_invoices_by_item').report_action(self, data=data)


class InvoicesbyItemReport(models.AbstractModel):
    _name = 'report.mgs_account.invoices_by_item_report'
    _description = 'Invoices by Item Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, product_id, is_group, invoices_bills):  # , company_branch_ids
        full_move = []
        params = []
        types = """('out_invoice', 'out_refund')"""

        if invoices_bills == 'Bills':
            types = """('in_invoice', 'in_refund')"""

        if is_group == 'all':
            select = """select COALESCE(sum(air.quantity), 0) as total_qty_all, COALESCE(sum(air.price_subtotal), 0) as total_amount_all"""
            order = ""

        if is_group == 'yes':
            select = """select pt.name as product_name, pp.id as product_id, COALESCE(sum(air.quantity), 0) as total_qty, COALESCE(sum(air.price_subtotal), 0) as total_amount"""
            order = """
            group by pt.name, pp.id
            order by pt.name
            """

        if is_group == 'no':
            select = """
            select air.invoice_date as date, concat(am.invoice_origin,' - ', am.name) as ref, rp.name as partner,
            am.id as move_id, pp.id as product_id,
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

        if product_id:
            from_where += """ and air.product_id = """ + str(product_id)

        if company_id:
            from_where += """ and air.company_id = """ + str(company_id)

        query = select + from_where + order

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

    # @api.model
    # def _get_cogs(self, move_id, product_id):
    #     params = [move_id, product_id, 'Cost of Revenue']
    #     query = """
    #     select sum(aml.debit) from account_move_line aml
    #     left join account_account aa on aml.account_id=aa.id
    #     left join account_account_type aat on aa.user_type_id=aat.id
    #     where aml.move_id = %s and aml.product_id = %s
    #     and aat.name = %s
    #     """
    #
    #     self.env.cr.execute(query, tuple(params))
    #
    #     contemp = self.env.cr.fetchone()
    #     if contemp is not None:
    #         result = contemp[0] or 0.0
    #     return result

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
            'invoices_bills': data['form']['invoices_bills'],
            'lines': self._lines,
            # 'get_cogs': self._get_cogs
        }
