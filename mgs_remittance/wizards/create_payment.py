# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MgsRemittancePaymentWizard(models.TransientModel):
    _name = 'mgs_remittance.payment.wizard'
    _description = 'Mgs Remittance Payment Wizard'

    journal_id = fields.Many2one(
        'account.journal', string='Cash/Bank Acc', domain=[('type', 'in', ['cash', 'bank'])], required=True)
    date = fields.Date(
        string='Date', default=lambda self: fields.Date.today(), required=True)
    memo = fields.Char(string='Memo')
    transaction_line_id = fields.Many2one(
        'mgs_remittance.transaction.line', string="Transaction Line", required=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    total = fields.Monetary(
        'Amount')

    @api.model
    def default_get(self, fields):
        rec = super(MgsRemittancePaymentWizard, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        transaction_line = self.env[active_model].browse(active_ids)

        rec.update({
            'transaction_line_id': transaction_line.id,
            'total': transaction_line.amount_due
        })
        return rec

    # @api.model
    def create_payment(self):
        # transaction_obj = self.env['mgs_remittance.transaction']
        transaction_line_obj = self.env['mgs_remittance.transaction.line']
        for r in self:
            if r.total > r.transaction_line_id.amount_due:
                raise UserError(
                    _('You can\'t pay more than %s') % r.transaction_line_id.amount_due)
            # Move vals:
            journal_id = r.journal_id
            company_id = r.company_id.id
            date = r.date
            ref = 'RID: %s' % str(
                r.transaction_line_id.related_transaction_id_no)
            transaction_line_id = r.transaction_line_id
            # Move_line vals
            move_line_name = r.transaction_line_id.related_transaction_id_ref
            # account_date = r.transaction_id.date
            related_transaction_id_no = int(
                r.transaction_line_id.related_transaction_id_no)
            src_partner_id = r.transaction_line_id.beneficiary_id.partner_id
            dst_partner_id = False
            account_src = src_partner_id.property_account_payable_id.id
            account_dst = r.journal_id.default_account_id.id
            currency_id = r.currency_id.id
            total_amount = r.total

            transaction_line_id.action_move_create(journal_id, company_id, date, ref, move_line_name,
                                                   src_partner_id, dst_partner_id, account_src, account_dst, currency_id, total_amount)

            # r.transaction_line_id.move_ids = [(4, move.id)]
            r.transaction_line_id.state = 'paid' if transaction_line_id.amount == transaction_line_id.amount_paid else 'approved'

            transaction_line_obj.sudo().search([('id', '=',
                                               related_transaction_id_no)]).state = 'paid'
            transaction_line_obj.sudo().search(
                [('id', '=', related_transaction_id_no)]).transaction_id._compute_is_paid_all()
            transaction_line_obj.sudo().search(
                [('id', '=', related_transaction_id_no)]).transaction_id.onchange_is_paid_all()
