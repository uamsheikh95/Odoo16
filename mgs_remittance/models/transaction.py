# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from itertools import groupby


class MGSRemittanceTransaction(models.Model):
    _name = 'mgs_remittance.transaction'
    _description = 'MGS Remittance Transaction'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Name', copy=False, default='/')
    date = fields.Date('Date', default=lambda self: fields.Date.today())
    company_id = fields.Many2one('res.company', string='Source Agent',
                                 default=lambda self: self.env.company.id, required=True)

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    # Remitter
    sender_id = fields.Many2one(
        'mgs_remittance.remitter', required=True, string='Sender')
    s_mobile = fields.Char(string="S.Mobile", required=True)
    s_email = fields.Char(string="S.Email")
    s_country_id = fields.Many2one(
        'res.country', string="S.Country", required=True)
    s_city_id = fields.Many2one(
        'mgs_remittance.city', string="S.City", required=True)
    s_remarks = fields.Text(string='Remarks')
    s_id_no = fields.Char(string="S.Identity No.")
    s_guarantor = fields.Char(string='S.Guarantor', help="Damiin")

    transaction_line_ids = fields.One2many(
        'mgs_remittance.transaction.line', 'transaction_id', string="Transaction Lines")

    transaction_detail_ids = fields.One2many(
        'mgs_remittance.transaction.detail', 'transaction_id', string="Transaction Details")

    state = fields.Selection([('draft', 'To Approve'), ('approved', 'Source Approved'),
                              ('ready', 'Ready to Pay'), ('paid', 'Paid'),
                              ('cancel', 'Cancelled')], default='draft')

    total = fields.Monetary(
        'Total Amount', compute='_compute_total', store=True)

    transaction_id = fields.Many2one(
        'mgs_remittance.transaction', string='Transaction', index=True)

    move_ids = fields.Many2many(
        'account.move', string='Journal Entries', ondelete='restrict', copy=False, readonly=True)

    is_approved_all = fields.Boolean(
        default=False, compute='_compute_is_approved_all')
    is_paid_all = fields.Boolean(
        default=False, compute='_compute_is_paid_all')
    remmitence_move_group_by = fields.Selection(
        [('beneficiary', 'Beneficiary'), ('journal', 'Journal')], string='Group by')
    approved_by = fields.Many2one(
        'res.users', string="Approved by", index=True)
    approve_date = fields.Datetime(string="Approve Date")

    @api.depends('transaction_line_ids', 'transaction_line_ids.state')
    def _compute_is_approved_all(self):
        for r in self:
            is_approved_all = False
            if len(r.transaction_line_ids) > 0:
                is_approved_all = True

            for transaction in r.transaction_line_ids:
                if transaction.state != 'approved':
                    is_approved_all = False
                    break

            r.is_approved_all = is_approved_all

    @api.depends('transaction_line_ids', 'transaction_line_ids.state')
    def _compute_is_paid_all(self):
        for r in self:
            is_paid_all = False
            if len(r.transaction_line_ids) > 0:
                is_paid_all = True

            for transaction in r.transaction_line_ids:
                if transaction.state != 'paid':
                    is_paid_all = False
                    break
            r.is_paid_all = is_paid_all

    @api.onchange('is_approved_all')
    def onchange_is_approved_all(self):
        for r in self:
            if r.is_approved_all:
                r.state = 'approved'

    @api.onchange('is_paid_all')
    def onchange_is_paid_all(self):
        for r in self:
            if r.is_paid_all:
                r.state = 'paid'

    @api.onchange('sender_id')
    def _onchange_sender_id(self):
        for r in self:
            if r.sender_id:
                r.s_mobile = r.sender_id.mobile
                r.s_email = r.sender_id.email
                r.s_country_id = r.sender_id.country_id.id
                r.s_city_id = r.sender_id.city_id.id
                r.s_id_no = r.sender_id.id_no
                r.s_guarantor = r.sender_id.guarantor

    @api.depends('transaction_line_ids', 'transaction_line_ids.total')
    def _compute_total(self):
        total = 0
        for r in self:
            for line in r.transaction_line_ids:
                total += line.total
        r.total = total

    def action_submit(self):
        for r in self:
            if len(r.transaction_line_ids) == 0:
                raise UserError(
                    _('Please add beneficiarie(s) to submit this transaction'))

            r.name = self.env['ir.sequence'].next_by_code(
                'mgs_remittance.transaction.seq')

    def action_approve(self):
        # print('------------------------------------------------------------------')
        # # res = []
        # # for transaction in r.transaction_line_ids:
        # #     res.append(type(transaction))
        # # r.r_remarks = str(res)
        for r in self:
            for transaction in r.transaction_line_ids:
                transaction.create_against_transaction_line()
            r.action_submit()
            r.action_move_create()
            r.state = 'approved'
            r.approved_by = self.env.user
            r.approve_date = fields.Datetime.now()

    def _prepare_move_values(self, journal_id, company_id, date, ref, currency_id):
        """
        This function prepares move values related to a remittance transaction
        """
        # self.ensure_one()

        move_values = {
            'journal_id': journal_id.id,
            'company_id': company_id,
            'date': date,
            'ref': ref,
            'currency_id': currency_id,
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # to set it to '' which cause no number to be given to the account.move when posted.
            'name': '/',
        }
        return move_values

    def _prepare_move_line_values(self, transaction):
        move_line_values = []
        transaction_id = transaction.transaction_id

        move_line_name = 'From: %s To: %s Amount#: %s (%s)' % (
            transaction_id.sender_id.name, transaction.beneficiary_id.name, transaction.total, transaction_id.company_id.name)
        account_date = transaction_id.date
        partner_id = transaction.destination_company_partner_id
        account_src = transaction.journal_id.default_account_id.id
        account_dst = partner_id.property_account_receivable_id.id
        currency_id = transaction.currency_id.id
        apply_commission = transaction.apply_commission
        commission_amount = transaction.commission_amount
        amount_without_commission = transaction.amount
        total_amount = transaction.total
        commission_config_acc_id_no = self.env['ir.config_parameter'].sudo(
        ).get_param('mgs_remittance.remmitence_commission_account_id')
        commission_config_acc_id = self.env['account.account'].search(
            [('id', '=', int(commission_config_acc_id_no))])

        if apply_commission and not commission_config_acc_id:
            raise UserError(
                _('Please define an income account for the commissions in the configuration'))

        # first line
        move_line_src = {
            'name': move_line_name,
            'debit': total_amount,
            'credit': 0,
            'partner_id': partner_id.id,
            'account_id': account_src,
            'date_maturity': account_date,
            'currency_id': currency_id,
            # 'exclude_from_invoice_tab': True,
        }

        if transaction.payment_method == 'Balance':
            move_line_src['partner_id'] = transaction.transaction_id.sender_id.partner_id.id
            # move_line_src['debit'] = transaction.transaction_id.sender_id.partner_id.debit
            move_line_src['account_id'] = transaction.transaction_id.sender_id.partner_id.property_account_payable_id.id

        move_line_values.append((0, 0, move_line_src))

        # second move line
        move_line_dst = {
            'name': move_line_name,
            'quantity': 1,
            'debit': 0,
            'credit': total_amount if not apply_commission else amount_without_commission,
            'account_id': account_dst,
            'partner_id': partner_id.id,
            'currency_id': currency_id,
        }
        move_line_values.append((0, 0, move_line_dst))

        if apply_commission:
            # second move line
            commission_line = {
                'name': move_line_name,
                'quantity': 1,
                'debit': 0,
                'credit': commission_amount,
                'account_id': commission_config_acc_id.id,
                # 'partner_id': partner_id.id,
                'currency_id': currency_id,
            }
            move_line_values.append((0, 0, commission_line))
        return move_line_values

    def _get_account_move_line_values(self, transaction_line_ids, move_line_values):
        commission_amount = 0
        for transaction in transaction_line_ids:
            move_line_name = transaction.transaction_id.name
            account_date = transaction.transaction_id.date
            partner_id = transaction.destination_company_partner_id
            account_src = transaction.journal_id.default_account_id.id
            account_dst = partner_id.property_account_receivable_id.id
            currency_id = transaction.currency_id.id
            apply_commission = transaction.apply_commission
            commission_amount = transaction.commission_amount
            amount_without_commission = transaction.amount
            total_amount = transaction.total
            commission_config_acc_id_no = self.env['ir.config_parameter'].sudo(
            ).get_param('mgs_remittance.remmitence_commission_account_id')
            commission_config_acc_id = self.env['account.account'].search(
                [('id', '=', int(commission_config_acc_id_no))])

            if apply_commission and not commission_config_acc_id:
                raise UserError(
                    _('Please define an income account for the commissions in the configuration'))

            # first line
            move_line_src = {
                'name': move_line_name,
                'debit': total_amount,
                'credit': 0,
                'partner_id': partner_id.id,
                'account_id': account_src,
                'date_maturity': account_date,
                'currency_id': currency_id,
                # 'exclude_from_invoice_tab': True,
            }

            move_line_values.append((0, 0, move_line_src))

            # second move line
            move_line_dst = {
                'name': move_line_name,
                'quantity': 1,
                'debit': 0,
                'credit': total_amount if not apply_commission else amount_without_commission,
                'account_id': account_dst,
                'partner_id': partner_id.id,
                'currency_id': currency_id,
            }
            move_line_values.append((0, 0, move_line_dst))

            if apply_commission:
                # second move line
                commission_line = {
                    'name': move_line_name,
                    'quantity': 1,
                    'debit': 0,
                    'credit': commission_amount,
                    'account_id': commission_config_acc_id.id,
                    # 'partner_id': partner_id.id,
                    'currency_id': currency_id,
                }
                move_line_values.append((0, 0, commission_line))

    # def _group_transaction_line_by_journal(self):
    #     default_move_group_by = self.remmitence_move_group_by

    #     # Raise an exception if not default default_move_group_by selected
    #     # if not default_move_group_by:
    #     #     raise UserError(
    #     #             _('Please choose a default journal entry group by'))
    #     journal_ids = []
    #     journals = []
    #     for r in self:
    #         r.s_remarks = str(default_move_group_by) or 'zn'

    #         if r.remmitence_move_group_by == 'beneficiary':
    #             for line in r.transaction_line_ids:
    #                 journals.append(line.journal_id)
    #             return journals

    #         # if default_move_group_by == journal
    #         for line in r.transaction_line_ids:
    #             if line.journal_id.id not in journal_ids:
    #                 journal_ids.append(line.journal_id.id)
    #                 journals.append(line.journal_id)
    #     return journals

    def action_move_create(self):
        for r in self:
            transaction_line_ids = r.transaction_line_ids
            company_id = r.company_id.id
            date = r.date
            currency_id = r.currency_id.id
            # ref = self.name

            for line in r.transaction_line_ids:
                ref = 'RID: %s' % str(line.id)
                journal_id = line.journal_id if line.payment_method == 'Cash' else line.company_id.remmitence_payout_journal_id
                move_vals = r._prepare_move_values(
                    journal_id, company_id, date, ref, currency_id)
                move_line_vals = r._prepare_move_line_values(line)

                move = self.env['account.move'].with_context(
                    default_journal_id=move_vals['journal_id']).create(move_vals)
                move['line_ids'] = move_line_vals
                move.action_post()
                self.write({
                    'move_ids': [(4, move.id)]
                })

            # OLD CODE
            # Fix later
            # if r.remmitence_move_group_by == 'journal':
            #     for journal in self._group_transaction_line_by_journal():
            #         journal_id = journal
            #         move_vals = r._prepare_move_values(
            #             journal_id, company_id, date, ref)
            #         filtered_transaction_lines = transaction_line_ids.filtered(
            #             lambda l: l.journal_id.id == journal_id.id)
            #         move_line_vals = r._prepare_move_line_values(
            #             filtered_transaction_lines)

            #         move = self.env['account.move'].with_context(
            #             default_journal_id=move_vals['journal_id']).create(move_vals)
            #         move['line_ids'] = move_line_vals
            #         move.action_post()
            #         self.write({
            #             'move_ids': [(4, move.id)]
            #         })
            # elif r.remmitence_move_group_by == 'beneficiary':
            #     for line in r.transaction_line_ids:
            #         journal_id = line.journal_id
            #         move_vals = r._prepare_move_values(
            #             journal_id, company_id, date, ref)
            #         filtered_transaction_lines = transaction_line_ids.filtered(
            #             lambda l: l.id == line.id)
            #         move_line_vals = r._prepare_move_line_values(
            #             filtered_transaction_lines)

            #         move = self.env['account.move'].with_context(
            #             default_journal_id=move_vals['journal_id']).create(move_vals)
            #         move['line_ids'] = move_line_vals
            #         move.action_post()
            #         self.write({
            #             'move_ids': [(4, move.id)]
            #         })
        return True

    def button_open_journal_entry(self):
        ''' Redirect the user to this transaction journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.move_ids.ids)],
            'context': {'create': False},
            'view_mode': 'tree,form'
        }


class MGSRemittanceTransactionLine(models.Model):
    _name = 'mgs_remittance.transaction.line'
    _description = 'MGS Remittance Transaction Line'
    _rec_name = 'beneficiary_id'
    _order = 'id desc'

    destination_company_partner_id = fields.Many2one(
        'res.partner', string='Destination Agent', index=True)
    approval_date = fields.Date(
        'Date', default=lambda self: fields.Date.today())
    source_company_partner_id = fields.Many2one(
        'res.partner', string='Source Agent', index=True)

    # Remitter
    sender_id = fields.Many2one(
        'mgs_remittance.remitter', string='Remitter')
    s_mobile = fields.Char(string="S.Mobile")
    s_email = fields.Char(string="S.Email")
    s_country_id = fields.Many2one(
        'res.country', string="S.Country")
    s_city_id = fields.Many2one(
        'mgs_remittance.city', string="S.City")
    s_remarks = fields.Text(string='S.Remarks')
    s_id_no = fields.Char(string="S.Identity No.")
    s_guarantor = fields.Char(string='S.Guarantor', help="Damiin")
    s_amount = fields.Float(
        'Received Amount', compute="_compute_source_amount_currency")
    s_currency_id = fields.Many2one('res.currency', 'Received Currency', domain=[(
        'active', '=', True)], default=lambda self: self.env.company.currency_id.id, compute="_compute_source_amount_currency")

    @api.depends('related_transaction_id_no', 'is_against_transaction_line')
    def _compute_source_amount_currency(self):
        for r in self:
            r.s_amount = 0
            r.s_currency_id = False

            transaction_line_obj = self.env['mgs_remittance.transaction.line']
            domain = [('id', '=', r.related_transaction_id_no)]
            if r.related_transaction_id_no and r.is_against_transaction_line:
                transaction_line_id = transaction_line_obj.sudo().search(domain)
                r.s_amount = transaction_line_id.amount
                r.s_currency_id = transaction_line_id.currency_id.id

    # Beneficiary
    beneficiary_id = fields.Many2one(
        'mgs_remittance.beneficiary', required=True, string='Beneficiary')
    b_mobile = fields.Char(string="B.Mobile", required=True)
    b_email = fields.Char(string="B.Email")
    b_country_id = fields.Many2one(
        'res.country', string="B.Country", required=True)
    b_city_id = fields.Many2one(
        'mgs_remittance.city', string="B.City", required=True)
    b_remarks = fields.Text(string='B.Remarks')
    b_id_no = fields.Char(string="B.Identity No.")
    b_guarantor = fields.Char(string='B.Guarantor', help="Damiin")

    related_transaction_id_no = fields.Integer(
        string='Against Transaction ID', readonly=True)
    related_transaction_id_ref = fields.Char(string='Source', readonly=True)
    is_against_transaction_line = fields.Boolean(
        string='Against Transaction', default=False, readonly=True)

    journal_id = fields.Many2one(
        'account.journal', string="Cash/Bank Acc", domain=[('type', 'in', ['cash', 'bank'])])
    payment_method = fields.Selection(
        [('Cash', 'Cash'), ('Balance', 'Balance')], default='Cash', required=True)
    sender_balance = fields.Monetary(
        'Balance', related='transaction_id.sender_id.partner_id.debit')
    amount = fields.Monetary('Amount', required=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', domain=[(
        'active', '=', True)], default=lambda self: self.env.company.currency_id.id)
    apply_commission = fields.Boolean(string='Apply Commission', default=False)
    commission_amount = fields.Monetary('Commission Amount')
    total = fields.Monetary(
        'Total Amount', default=0.0, compute='_compute_total', store=True)
    # paid_amount = fields.Monetary(
    #     'Total Amount', default=0.0, compute='_compute_paid_amount', store=True)
    transaction_id = fields.Many2one(
        'mgs_remittance.transaction', string='Transaction', index=True)

    state = fields.Selection([('draft', 'Draft'), ('waiting', 'Waiting for Approval'), ('to_approve', 'To Approve'),
                              ('approved', 'Ready to Pay'), ('paid', 'Paid'), ('cancel', 'Cancelled')], default='draft')
    move_ids = fields.Many2many(
        'account.move', string='Journal Entries', ondelete='restrict', copy=False, readonly=True)

    # Approval
    approved_by = fields.Many2one(
        'res.users', string="Approved by", index=True)
    approve_date = fields.Datetime(string="Approve Date")

    remit_date = fields.Date('Remit Date')

    amount_due = fields.Monetary(
        'Amout Due', default=0.0, compute='_compute_amounts', store=True)
    amount_paid = fields.Monetary(
        'Amout Paid', default=0.0, compute='_compute_amounts', store=True)

    @api.onchange('amount_due', 'move_ids')
    def onchange_amount_due(self):
        for r in self:
            if r.amount_due != 0:
                r.state = 'approved'

    # def write(self, vals):
    #     vals['state'] = 'paid' if vals['amount_due'] == 0 else 'approved'
    #     res = super(MGSRemittanceTransactionLine, self).write(vals)
    #     self.onchange_amount_due()
    #     return res

    @api.depends('move_ids', 'move_ids.amount_total')
    def _compute_amounts(self):
        amount_due = 0
        move_line_obj = self.env['account.move.line']
        for r in self:
            r.amount_due = r.amount
            r.amount_paid = 0
            if len(r.move_ids) == 0:
                return True
            partner_id = r.beneficiary_id.partner_id.id
            amount = r.amount
            domain = [('move_id', 'in', r.move_ids.ids),
                      ('partner_id', '=', partner_id),
                      ('parent_state', '=', 'posted')]

            for move_line in move_line_obj.search(domain):
                amount_due += move_line.credit - move_line.debit

            r.amount_due = amount_due
            r.amount_paid = amount - amount_due

    @api.onchange('destination_company_partner_id')
    def _onchange_destination_company_partner_id(self):
        partner_ids = []
        for company in self.env['res.company'].sudo().search([('id', '!=', self.transaction_id.company_id.id)]):
            if company.partner_id.id not in partner_ids:
                partner_ids.append(company.partner_id.id)

        return {'domain': {'destination_company_partner_id': [('id', 'in', partner_ids)]}}

    @api.onchange('beneficiary_id')
    def _onchange_beneficiary_id(self):
        for r in self:
            if r.beneficiary_id:
                r.b_mobile = r.beneficiary_id.mobile
                r.b_email = r.beneficiary_id.email
                r.b_country_id = r.beneficiary_id.country_id.id
                r.b_city_id = r.beneficiary_id.city_id.id
                r.b_id_no = r.beneficiary_id.id_no
                r.b_guarantor = r.beneficiary_id.guarantor

    @api.depends('amount', 'apply_commission', 'commission_amount')
    def _compute_total(self):
        for r in self:
            r.total = r.amount if not r.apply_commission else r.amount + r.commission_amount

    @api.model
    def prepare_against_transaction_line(self):
        company_id = self.env['res.company'].sudo().search(
            [('partner_id', '=', self.destination_company_partner_id.id)])

        amount = self.amount
        currency_id = company_id.currency_id
        source_currency_id = self.currency_id
        if currency_id.id != source_currency_id.id:
            amount = amount / currency_id.inverse_rate

        transaction_line_vals = {
            'destination_company_partner_id': self.destination_company_partner_id.id,
            'source_company_partner_id': self.company_id.partner_id.id,
            'remit_date': self.transaction_id.date,
            # Remitter
            'sender_id': self.transaction_id.sender_id.id,
            's_mobile': self.transaction_id.s_mobile,
            's_email':  self.transaction_id.s_email,
            's_country_id': self.transaction_id.s_country_id.id,
            's_city_id': self.transaction_id.s_city_id.id,
            's_remarks': self.transaction_id.s_remarks,
            's_id_no': self.transaction_id.s_id_no,
            's_guarantor': self.transaction_id.s_guarantor,
            # Beneficiary
            'beneficiary_id': self.beneficiary_id.id,
            'b_mobile': self.b_mobile,
            'b_email':  self.b_email,
            'b_country_id': self.b_country_id.id,
            'b_city_id': self.b_city_id.id,
            'b_remarks': self.b_remarks,
            'b_id_no': self.b_id_no,
            'b_guarantor': self.b_guarantor,
            'related_transaction_id_no': self.id,
            'related_transaction_id_ref': self.transaction_id.name,
            'is_against_transaction_line': True,
            'amount': amount,
            'company_id': company_id.id,
            'currency_id': company_id.currency_id.id,
            'apply_commission': self.apply_commission,
            'commission_amount': self.commission_amount,
            'state': 'to_approve'
        }

        return transaction_line_vals

    @api.model
    def create_against_transaction_line(self):
        transaction_line_vals = self.prepare_against_transaction_line()
        inserted_transation_line = self.sudo().create(transaction_line_vals)
        for r in self:
            r.related_transaction_id_no = inserted_transation_line.id
            r.state = 'waiting'

    def action_approve(self):
        config_payout_journal_id_no = self.env['ir.config_parameter'].sudo(
        ).get_param('mgs_remittance.remmitence_payout_journal_id')
        config_payout_journal_id = self.env.company.remmitence_payout_journal_id

        if not config_payout_journal_id:
            raise UserError(
                _('Please define a default journal for payout transactions in the remittance settings'))
        for r in self:

            # ============================ JOURNAL CREATION ============================
            # Move vals:
            journal_id = config_payout_journal_id
            company_id = r.company_id.id
            date = r.approval_date
            ref = 'RID/%s' % str(r.related_transaction_id_no)
            # Move_line vals
            # move_line_name = r.transaction_id.name
            move_line_name = 'From: %s To: %s Amount: %s (%s)' % (
                r.sender_id.name, r.beneficiary_id.name, r.total, r.company_id.name)
            # account_date = r.transaction_id.date
            src_partner_id = r.source_company_partner_id
            dst_partner_id = r.beneficiary_id.partner_id
            account_src = src_partner_id.property_account_payable_id.id
            account_dst = dst_partner_id.property_account_payable_id.id
            currency_id = r.currency_id.id
            total_amount = r.total

            related_transaction_id_no = int(r.related_transaction_id_no)

            move = self.action_move_create(journal_id, company_id, date, ref, move_line_name,
                                           src_partner_id, dst_partner_id, account_src, account_dst, currency_id, total_amount)

            r.state = 'approved'
            r.approved_by = self.env.user
            r.approve_date = fields.Datetime.now()
            self.env['mgs_remittance.transaction.line'].sudo().search(
                [('id', '=', related_transaction_id_no)]).state = 'approved'

            self.env['mgs_remittance.transaction.line'].sudo().search(
                [('id', '=', related_transaction_id_no)]).transaction_id._compute_is_approved_all()
            self.env['mgs_remittance.transaction.line'].sudo().search(
                [('id', '=', related_transaction_id_no)]).transaction_id.onchange_is_approved_all()

    def _prepare_move_line_values(self, move_line_name, src_partner_id, dst_partner_id, account_src, account_dst, currency_id, total_amount):
        move_line_values = []
        # first line
        move_line_src = {
            'name': move_line_name,
            'debit': total_amount,
            'credit': 0,
            'account_id': account_src,
            'partner_id': src_partner_id.id,
            # 'date_maturity': account_date,
            'currency_id': currency_id,
            # 'exclude_from_invoice_tab': True,
        }

        move_line_values.append((0, 0, move_line_src))

        # second move line
        move_line_dst = {
            'name': move_line_name,
            'quantity': 1,
            'debit': 0,
            'credit': total_amount,
            'account_id': account_dst,
            'currency_id': currency_id,
        }
        if dst_partner_id:
            move_line_dst['partner_id'] = dst_partner_id.id
        move_line_values.append((0, 0, move_line_dst))

        return move_line_values

    def action_move_create(self, journal_id, company_id, date, ref, move_line_name, src_partner_id, dst_partner_id, account_src, account_dst, currency_id, total_amount):
        ransaction_obj = self.env['mgs_remittance.transaction']
        for r in self:
            move_vals = ransaction_obj._prepare_move_values(
                journal_id, company_id, date, ref, currency_id)

            # Move_line vals:
            line_ids = r._prepare_move_line_values(
                move_line_name, src_partner_id, dst_partner_id, account_src, account_dst, currency_id, total_amount)

            move = self.env['account.move'].with_context(
                default_journal_id=move_vals['journal_id']).create(move_vals)
            move['line_ids'] = line_ids
            move.action_post()
            self.move_ids = [(4, move.id)]
            # return move

    def button_open_journal_entry(self):
        ''' Redirect the user to this transaction journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Journal Entries"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False, 'edit': True},
            'domain': [('id', 'in', self.move_ids.ids)],
            'view_mode': 'tree,form'
        }


class MGSRemittanceTransactionDetail(models.Model):
    _name = 'mgs_remittance.transaction.detail'
    _description = 'MGS Remittance Transaction Detail'

    date = fields.Date('Date', default=lambda self: fields.Date.today())
    journal_name = fields.Char('Journal')
    remarks = fields.Char('Memo')
    amount = fields.Monetary('Amount', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)

    transaction_id = fields.Many2one(
        'mgs_remittance.transaction', string='Transaction', index=True)
