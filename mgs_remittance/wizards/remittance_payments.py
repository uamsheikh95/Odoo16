# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MgsRemittanceRemittancePayments(models.TransientModel):
    _name = 'mgs_remittance.remittance_payments'
    _description = 'Mgs Remittance Remittance Payments'

    rem_id = fields.Integer(string='Rem ID')

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'rem_id': self.rem_id,
            },
        }

        return self.env.ref('mgs_remittance.action_remittance_payments_report').report_action(self, data=data)


class MgsRemittancePaymentsReport(models.AbstractModel):
    _name = 'report.mgs_remittance.remittance_payments_report'
    _description = 'Mgs Remittance Remittance Payments Report'

    def lines(self, rem_id):
        payment_ids = []
        transaction_line_obj = self.env['mgs_remittance.transaction.line']
        move_line_obj = self.env['account.move.line']
        domain = [('related_transaction_id_no', '=', rem_id)]
        transaction_line_id = transaction_line_obj.sudo().search(domain)
        partner_id = transaction_line_id.beneficiary_id.partner_id.id
        move_ids = transaction_line_id.move_ids

        for move in move_ids:
            for move_line in move.line_ids:
                if move_line.account_id.account_type == 'liability_payable' and move_line.debit > 0 and move_line.partner_id.id == partner_id:
                    payment_ids.append(move_line)
        return payment_ids

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'rem_id': data['form']['rem_id'],
            'payment_ids': self.lines(data['form']['rem_id']),
        }
