from odoo import tools
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PurchaseReport(models.Model):
    _inherit = 'purchase.report'

    def _query(self, with_clause='', fields=None, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""
        return '%s (%s %s WHERE l.display_type IS NULL %s)' % \
               (with_, self._select(), self._from(), self._group_by())

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (
            self._table, self._query()))


class PurchasesbyVendorDetail(models.TransientModel):
    _name = 'mgs_purchase.purchases_by_vendor'
    _description = 'Purchases by Vendor Detail'

    partner_id = fields.Many2one('res.partner', string="Partner")
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
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
            },
        }

        return self.env.ref('mgs_purchase.action_purchases_by_vendor').report_action(self, data=data)


class PurchasesbyVendorDetailReport(models.AbstractModel):
    _name = 'report.mgs_purchase.purchases_by_vendor_report'
    _description = 'Purchases by Vendor Detail Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id, is_group):  # , company_branch_ids
        full_move = []
        params = []

        if is_group == 'all':
            select = """select COALESCE(sum(pr.qty_ordered), 0) as total_qty_ordered_all, COALESCE(sum(pr.qty_received), 0) as total_qty_received_all,
            COALESCE(sum(pr.qty_billed), 0) as total_qty_billed_all, COALESCE(sum(pr.qty_to_be_billed), 0) as total_qty_to_be_billed_all,
            COALESCE(sum(amount_total), 0) as total_amount_all"""
            order = ""

        if is_group == 'yes':
            select = """select rp.name as partner_name, rp.id as partner_id,
            COALESCE(sum(pr.qty_ordered), 0) as total_qty_ordered, COALESCE(sum(pr.qty_received), 0) as total_qty_received,
            COALESCE(sum(pr.qty_billed), 0) as total_qty_billed, COALESCE(sum(pr.qty_to_be_billed), 0) as total_qty_to_be_billed,
            COALESCE(sum(amount_total), 0) as total_amount"""
            order = """
            group by rp.name, rp.id
            order by rp.name
            """

        if is_group == 'no':
            select = """
            select pr.date_order, po.name as order_no, pt.name as product,
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

        if partner_id:
            from_where += """ and pr.partner_id = """ + str(partner_id)

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
            'partner_id': data['form']['partner_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'lines': self._lines,
        }
