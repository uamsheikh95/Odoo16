# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MgsRemittanceSearchTrans(models.TransientModel):
    _name = 'mgs_remittance.search_trans'
    _description = 'Mgs Remittance Search Transaction'

    rem_id = fields.Integer(string='Rem ID')

    # Source Details
    date = fields.Date('Tran Date', readonly=True)
    state = fields.Selection([('draft', 'To Approve'), ('approved', 'Source Approved'),
                              ('ready', 'Ready to Pay'), ('paid', 'Paid'),
                              ('cancel', 'Cancelled')], readonly=True)
    amount = fields.Float('Amount', readonly=True)

    source_company_partner_id = fields.Many2one(
        'res.partner', string='Source Agent', index=True, readonly=True)

    sender_id = fields.Many2one(
        'mgs_remittance.remitter', string='Remitter', readonly=True)

    s_country_id = fields.Many2one(
        'res.country', string="Source Country", readonly=True)

    # ++++++++++
    destination_company_partner_id = fields.Many2one(
        'res.partner', string='Destination Agent', index=True, readonly=True)
    b_country_id = fields.Many2one(
        'res.country', string="B.Country", readonly=True)
    b_city_id = fields.Many2one(
        'mgs_remittance.city', string="B.City", readonly=True)
    beneficiary_id = fields.Many2one(
        'mgs_remittance.beneficiary', string='Beneficiary', readonly=True)
    b_mobile = fields.Char(string="B.Mobile", readonly=True)

    @api.onchange('rem_id')
    def onchange_rem_id(self):
        transaction_line_obj = self.env['mgs_remittance.transaction.line']
        if self.rem_id:
            domain = [('id', '=', self.rem_id)]
            transaction_line_id = transaction_line_obj.search(domain)
            self.write({
                # Source Vals
                'date': transaction_line_id.transaction_id.date,
                'state': transaction_line_id.state,
                'amount': transaction_line_id.amount,
                'source_company_partner_id': transaction_line_id.source_company_partner_id.id,
                'sender_id': transaction_line_id.sender_id.id,
                's_country_id': transaction_line_id.s_country_id.id,
                # Destination Vals
                'destination_company_partner_id': transaction_line_id.destination_company_partner_id.id,
                'b_country_id': transaction_line_id.b_country_id.id,
                'b_city_id': transaction_line_id.b_city_id.id,
                'beneficiary_id': transaction_line_id.beneficiary_id.id,
                'b_mobile': transaction_line_id.b_mobile,
            })
