# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    remmitence_commission_account_id = fields.Many2one(
        'account.account', string='Account')

    remmitence_payout_journal_id = fields.Many2one(
        'account.journal', string='Default Journal')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    remmitence_commission_account_id = fields.Many2one(
        'account.account', domain=[('account_type', '=', 'income')], related="company_id.remmitence_commission_account_id", readonly=False, string='Account')
    default_remmitence_move_group_by = fields.Selection(
        [('beneficiary', 'Beneficiary'), ('journal', 'Journal')], string='Group by', default='beneficiary', default_model='mgs_remittance.transaction')

    # remmitence_payout_journal_id = fields.Many2one(
    #     'account.journal', string='Default Journal', related="company_id.remmitence_payout_journal_id", readonly=False, config_parameter='mgs_remittance.remmitence_payout_journal_id')

    remmitence_payout_journal_id = fields.Many2one(
        'account.journal', related='company_id.remmitence_payout_journal_id', string='Default Journal', readonly=False)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param(
            'mgs_remittance.remmitence_payout_journal_id', self.remmitence_payout_journal_id)

    # def set_values(self):
    #     res = super(ResConfigSettings, self).set_values()
    # self.env['ir.config_parameter'].set_param('mgs_remittance.remmitence_commission_account_id',
    #                                           self.remmitence_commission_account_id.id)
    # self.env['ir.config_parameter'].set_param('mgs_remittance.remmitence_payout_journal_id',
    #                                           self.remmitence_payout_journal_id.id)
    # return res
    # self.env['ir.config_parameter'].set_param('mgs_remittance.remmitence_move_group_by',
    #                                           self.remmitence_move_group_by)
