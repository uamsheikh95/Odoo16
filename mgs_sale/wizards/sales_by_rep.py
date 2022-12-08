from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SalesbyRepDetail(models.TransientModel):
    _name = 'mgs_sale.sales_by_rep'
    _description = 'Sales by Rep'

    product_id = fields.Many2one('product.product', string="Product")
    partner_id = fields.Many2one('res.partner', string="Partner")
    team_id = fields.Many2one('crm.team', string="Salesteam")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)
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
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'team_id': [self.team_id.id, self.team_id.name],
                'user_id': [self.user_id.id, self.user_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
            },
        }

        return self.env.ref('mgs_sale.action_sales_by_rep').report_action(self, data=data)


class SalesbyRepDetailReport(models.AbstractModel):
    _name = 'report.mgs_sale.sales_by_rep_report'
    _description = 'Sales by Rep Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, product_id, partner_id, team_id, user_id):  # , company_branch_ids
        full_move = []
        params = []

        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"

        query = """
        select sr.date, sr.name as order_no, rp.name as partner, pt.name as product_name,
        COALESCE(sr.product_uom_qty, 0), COALESCE(sr.qty_delivered, 0), COALESCE(sr.qty_invoiced, 0), COALESCE(sr.qty_to_invoice, 0), COALESCE(sr.price_total, 0),
            sr.state, COALESCE(sr.price_total-sr.margin, 0) as cost, COALESCE(sr.margin, 0)
        from sale_report as sr
        left join res_partner as rp on sr.partner_id=rp.id
        left join product_product as pp on sr.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        where sr.state in ('sale', 'done', 'paid', 'pos_done', 'invoiced')
        """

        if date_from:
            params.append(f_date)
            query += """ and sr.date >= %s"""

        if date_to:
            params.append(t_date)
            query += """ and sr.date <= %s"""

        if product_id:
            query += """ and sr.product_id = """ + str(product_id)

        if partner_id:
            query += """ and sr.partner_id = """ + str(partner_id)

        if team_id:
            query += """ and sr.team_id = """ + str(team_id)

        if user_id:
            query += """ and sr.user_id = """ + str(user_id)

        if company_id:
            query += """ and sr.company_id = """ + str(company_id)

        query += "order by sr.date"

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
            'partner_id': data['form']['partner_id'],
            'team_id': data['form']['team_id'],
            'user_id': data['form']['user_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'lines': self._lines,
        }
