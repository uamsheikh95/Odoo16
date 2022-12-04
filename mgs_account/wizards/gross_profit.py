# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo import models, fields, api


class GrossProfit(models.TransientModel):
    _name = 'mgs_account.gross_profit'
    _description = 'Gross Profit Wizard'

    product_id = fields.Many2one('product.product', string="Product")
    partner_id = fields.Many2one('res.partner', string="Partner")
    # , default=lambda self: fields.Date.today().replace(day=1)
    date_from = fields.Date('From Date')
    # , default=lambda self: fields.Date.today()
    date_to = fields.Date('To Date')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id, required=True)
    report_by = fields.Selection(
        [('Product', 'Product'), ('Partner', 'Partner')], string='Group by', default='Product', required=True)
    target_moves = fields.Selection(
        [('all', 'All Entries'), ('posted', 'All Posted Entries')], string='Target Moves', default='all', required=True)
    product_type = fields.Selection([('all', 'All Products'), ('product', '	Storable Products'), (
        'service', 'Service Products')], string='Product Type', default='all', required=True)

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'company_id': [self.company_id.id, self.company_id.name],
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'product_id': [self.product_id.id, self.product_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'report_by': self.report_by,
                'target_moves': self.target_moves,
                'product_type': self.product_type,
            },
        }

        return self.env.ref('mgs_account.action_report_gross_profit').report_action(self, data=data)


class GrossProfitReport(models.AbstractModel):
    _name = 'report.mgs_account.gross_profit_report'
    _description = 'Gross Profit Report'

    def _lines(self, company_id, date_from, date_to, partner_id, product_id, target_moves, product_type, report_by):
        params = []
        states = "('posted','draft')"
        if target_moves == 'posted':
            states = "('posted')"

        select_query = """select pt.name as group, pt.default_code as default_code, pp.id as product_id,
        COALESCE(sum(aml.debit), 0) as act_cost,
        COALESCE(sum(aml.credit), 0) as act_revenue"""

        order_query = "group by pt.name, pt.default_code, pp.id order by pt.name"

        if report_by == 'Partner':
            select_query = """select rp.name as group,
            COALESCE(sum(aml.debit), 0) as act_cost,
            COALESCE(sum(aml.credit), 0) as act_revenue"""

            order_query = "group by rp.name order by rp.name"

        from_where_query = """
        from account_move_line as aml
        left join account_account as aa on aml.account_id=aa.id
        left join res_partner as rp on aml.partner_id=rp.id
        left join product_product as pp on aml.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        where aa.account_type in ('expense_direct_cost', 'income') and aml.parent_state in """ + states

        if date_from:
            params.append(date_from)
            from_where_query += " and aml.date >= %s"

        if date_to:
            params.append(date_to)
            from_where_query += " and aml.date <= %s"

        if report_by == 'Product' and product_id:
            from_where_query += " and aml.product_id = " + str(product_id)

            # if product_type == 'product':
            #     from_where_query += " and pt.product_tye = 'product"

            # if product_type == 'service':
            #     from_where_query += " and pt.product_tye = 'service"

        if report_by == 'Partner' and partner_id:
            from_where_query += " and aml.partner_id = " + str(partner_id)

        if company_id:
            from_where_query += " and aml.company_id = " + str(company_id)

        query = select_query + from_where_query + order_query

        self.env.cr.execute(query, tuple(params))
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
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to'],
            'product_id': data['form']['product_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'target_moves': data['form']['target_moves'],
            'product_type': data['form']['product_type'],
            'partner_id': data['form']['partner_id'],
            'lines': self._lines,
        }
