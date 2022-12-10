from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MGSInvoiceDetail(models.TransientModel):
    _name = 'mgs_account.invoice_detail'
    _description = 'MGS Invoice Detail'

    partner_id = fields.Many2one('res.partner', string="Partner")
    product_id = fields.Many2one('product.product', string="Product")
    team_id = fields.Many2one('crm.team', string="Salesteam")
    user_id = fields.Many2one('res.users', string='Salesperson')
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Term')
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
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'product_id': [self.product_id.id, self.product_id.name],
                'team_id': [self.team_id.id, self.team_id.name],
                'user_id': [self.user_id.id, self.user_id.name],
                'payment_term_id': [self.payment_term_id.id, self.payment_term_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
                'invoices_bills': self.invoices_bills,
            },
        }

        return self.env.ref('mgs_account.action_invoice_detail').report_action(self, data=data)


class MGSInvoiceDetailReport(models.AbstractModel):
    _name = 'report.mgs_account.invoice_detail_report'
    _description = 'MGS Invoice Detail Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id, product_id, team_id, user_id, payment_term_id, invoices_bills):  # , company_branch_ids
        full_move = []
        params = []
        types = """('out_invoice', 'out_refund')"""

        if invoices_bills == 'Bills':
            types = """('in_invoice', 'in_refund')"""

        query = """
        select air.invoice_date as date, concat(am.invoice_origin,' - ', am.name) as ref, concat(pt.name['en_US'],' - ', pt.default_code) as product,
        air.quantity as quantity, air.price_subtotal as amount_total, air.price_average as rate, air.state as state, rp.name as partner
        from account_invoice_report as air
        left join account_move as am on air.move_id=am.id
        left join res_partner as rp on air.partner_id=rp.id
        left join product_product as pp on air.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        where air.state = 'posted' and air.quantity != 0
        and air.move_type in """ + types

        if date_from:
            params.append(date_from)
            query += """ and air.invoice_date >= %s"""

        if date_to:
            params.append(date_to)
            query += """ and air.invoice_date <= %s"""

        if partner_id:
            query += """ and air.partner_id = """ + str(partner_id)

        if product_id:
            query += """ and air.product_id = """ + str(product_id)

        if team_id:
            query += """ and air.team_id = """ + str(team_id)

        if user_id:
            query += """ and air.invoice_user_id = """ + str(user_id)

        if payment_term_id:
            query += """ and am.invoice_payment_term_id = """ + \
                str(payment_term_id)

        if company_id:
            query += """ and air.company_id = """ + str(company_id)

        query += " order by air.invoice_date"

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
            'product_id': data['form']['product_id'],
            'team_id': data['form']['team_id'],
            'user_id': data['form']['user_id'],
            'payment_term_id': data['form']['payment_term_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'invoices_bills': data['form']['invoices_bills'],
            'lines': self._lines,
        }
