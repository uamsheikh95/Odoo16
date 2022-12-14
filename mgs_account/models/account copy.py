# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        line_vals_list = super(
            AccountPayment, self)._prepare_move_line_default_vals()

        payment_display_name = {
            'outbound-customer': _("Customer Reimbursement"),
            'inbound-customer': _("Customer Payment"),
            'outbound-supplier': _("Vendor Payment"),
            'inbound-supplier': _("Vendor Reimbursement"),
        }
        default_line_name = self.env['account.move.line']._get_default_line_name(
            _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (
                self.payment_type, self.partner_type)],
            self.amount,
            self.currency_id,
            self.date,
            partner=self.partner_id,
        )

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _(
                    'Transfer from %s', self.destination_journal_id.name)
            else:  # payment.payment_type == 'outbound':
                liquidity_line_name = _(
                    'Transfer to %s', self.destination_journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        line_vals_list[0]['name'] = liquidity_line_name or default_line_name

        return line_vals_list
