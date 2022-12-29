# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date
import hashlib
import requests
import json


class MgsSms(models.Model):
    _name = 'mgs.sms'
    _description = 'mgs sms'
    _rec_name = 'source_name'
    _order = 'datetime DESC'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    datetime = fields.Datetime()
    message = fields.Text()
    mobile = fields.Char()
    partner_id = fields.Many2one('res.partner')
    model_id = fields.Many2one('ir.model', string="Model")
    source_name = fields.Char()
    response = fields.Text()
    state = fields.Selection([('sent', 'Sent'), ('failed', 'Failed')])

    @api.model
    def get_partner_balance(self, id):
        partner_balance = """
                            select COALESCE(sum(aml.debit - aml.credit), 0)
                            from account_move_line as aml
                            left join account_account as aa on aml.account_id=aa.id
                            where aml.partner_id = %s""" % str(id) + """
                            and aa.account_type = 'asset_receivable'
                            and parent_state in ('draft', 'posted')"""
        self.env.cr.execute(partner_balance)
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    def action_send_sms(self):
        if not self.mobile:
            self.message_post(body='This partner has no mobile number')
            return True
        config_params = self._get_mgs_sms_config_params()
        # print(config_params)

        username = config_params['username']
        passowrd = config_params['passowrd']
        sender = config_params['sender']
        private_key = config_params['private_key']
        current_date = config_params['current_date']

        msg = self.message
        to = self.mobile

        msg = msg.replace(" ", "%20")
        hashkey = username + "|" + passowrd + "|" + to + "|" + msg + \
            "|" + sender + "|" + current_date + "|" + private_key
        hashkey = hashlib.md5(hashkey.encode('utf-8')).hexdigest()
        hashkey = str(hashkey).upper()
        url = "https://sms.mytelesom.com/index.php/Gateway/sendsms/%s/%s/%s/%s" % (
            sender, msg, to, hashkey)

        response = requests.get(url)
        self.write({'response': response.text})
        response = json.loads(response.text)
        if response['status'] == "error":
            self.write({'state': 'failed'})
        if response['status'] != "error":
            self.write({'state': 'sent'})
        return "SMS STATUS : " + response['status']

    @api.model
    def _get_mgs_sms_config_params(self):
        username = self.env.company.mgs_username
        passowrd = self.env.company.mgs_password
        sender = self.env.company.mgs_sender
        private_key = self.env.company.mgs_key
        current_date = datetime.strptime(
            str(date.today()), '%Y-%m-%d').strftime('%d/%m/%Y')
        return {'username': username, 'passowrd': passowrd, 'sender': sender, 'private_key': private_key, 'current_date': current_date}


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def send_mgs_sms(self):
        mgs_sms_obj = self.env['mgs.sms']
        model_obj = self.env['ir.model'].sudo().search(
            [('model', '=', self._inherit)]).id
        for rec in self:
            if rec.picking_type_id.code == 'outgoing':
                if not rec.partner_id.mobile:
                    rec.message_post(
                        body='This partner has no mobile number attached')
                products = ''
                if rec.move_ids_without_package:
                    for product in rec.move_ids_without_package:
                        products += ', %s - %s%s' % (
                            product.product_id.name, product.quantity_done, 'pcs')

                picking_no = rec.name.replace('/', ':')
                msg = 'DELIVERY: Macamiil waxa laguu soo raray dalabkaagii tixraac %s oo kala ah: %s' % (
                    picking_no, products)
                to = rec.partner_id.mobile

                sms_record = mgs_sms_obj.create({'source_name': rec.name, 'message': msg, 'mobile': to,
                                                'partner_id': rec.partner_id.id, 'model_id': model_obj, 'datetime': datetime.now()})
                if sms_record:
                    try:
                        response = sms_record.action_send_sms()
                        rec.message_post(body=response)
                    except Exception as e:
                        sms_record.message_post(body=str(e))

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        self.sudo().send_mgs_sms()
        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    def send_sms(self):
        mgs_sms_obj = self.env['mgs.sms']
        model_obj = self.env['ir.model'].sudo().search(
            [('model', '=', self._inherit)]).id
        for rec in self:
            if rec.move_type == 'out_invoice':
                if not rec.partner_id.mobile:
                    rec.message_post(
                        body='This partner has no mobile number attached')
                partner_balance = ''
                if rec.partner_id:
                    partner_balance += str(
                        mgs_sms_obj.get_partner_balance(rec.partner_id.id))

                invoice_number = rec.name.replace('/', '-')
                msg = 'INVOICE: Macamiil waxa xisaabtaada lagu dalacay iib dhan USD %s tixraac %s deyntaada cusbi waa USD %s' % (
                    rec.amount_total, invoice_number, partner_balance)
                to = rec.partner_id.mobile or None
                sms_record = mgs_sms_obj.create({'source_name': rec.name, 'message': msg, 'mobile': to,
                                                'partner_id': rec.partner_id.id, 'model_id': model_obj, 'datetime': datetime.now()})
                if sms_record:
                    try:
                        response = sms_record.action_send_sms()
                        rec.message_post(body=response)
                    except Exception as e:
                        sms_record.message_post(body=str(e))

    def action_post(self):
        res = super(AccountMove, self).action_post()
        self.sudo().send_sms()
        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def send_sms(self):
        mgs_sms_obj = self.env['mgs.sms']
        model_obj = self.env['ir.model'].sudo().search(
            [('model', '=', self._inherit)]).id
        for rec in self:
            if rec.payment_type == 'inbound':
                if not rec.partner_id.mobile:
                    rec.message_post(
                        body='This partner has no mobile number attached')
                partner_balance = ''
                if rec.partner_id:
                    partner_balance += str(
                        mgs_sms_obj.get_partner_balance(rec.partner_id.id))
                payment_number = ''
                if rec.name:
                    payment_number = rec.name.replace('.', '-')
                    payment_number = rec.name.replace('/', '-')

                msg = 'PAYMENT: Macamiil waxaad soo bixisay lacag dhan USD %s tixraac %s deynta kugu hadhay hadda waa USD %s' % (
                    rec.amount, payment_number, partner_balance)
                to = rec.partner_id.mobile or None
                sms_record = mgs_sms_obj.create({'source_name': rec.name, 'message': msg, 'mobile': to,
                                                'partner_id': rec.partner_id.id, 'model_id': model_obj, 'datetime': datetime.now()})
                if sms_record:
                    try:
                        response = sms_record.action_send_sms()
                        rec.message_post(body=response)
                    except Exception as e:
                        sms_record.message_post(body=str(e))

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        self.sudo().send_sms()
        return res


class ResCompany(models.Model):
    _inherit = 'res.company'

    sms_type = fields.Selection(
        [('Telesom', 'Telesom'), ('Golis', 'Golis')], default='Telesom', string="SMS Type")

    mgs_username = fields.Char(
        string='Telesom Username')
    mgs_password = fields.Char(
        string='Telesom Password')
    mgs_sender = fields.Char(string='Telesom Sender Name')
    mgs_key = fields.Char(
        string='Telesom SMS Key')

    mgs_golis_sender = fields.Char(
        string='Golis Sender Name')
    mgs_golis_token = fields.Char(
        string='Golis Key')
    mgs_golis_overwrite_odoo_sms = fields.Boolean(
        string='Golis Overwrite odoo sms', default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sms_type = fields.Selection(
        [('Telesom', 'Telesom'), ('Golis', 'Golis')], related='company_id.sms_type', readonly=False, string="SMS Type")

    # ------------------------------------------- Telesom -------------------------------------------
    mgs_username = fields.Char(
        string='Telesom Username', related="company_id.mgs_username", readonly=False)
    mgs_password = fields.Char(
        string='Telesom Password', related="company_id.mgs_password", readonly=False)
    mgs_sender = fields.Char(
        string='Telesom Sender Name', related="company_id.mgs_sender", readonly=False)
    mgs_key = fields.Char(
        string='Telesom Key', related="company_id.mgs_key", readonly=False)

    # -------------------------------------------  Golis  -------------------------------------------
    mgs_golis_sender = fields.Char(
        string='Golis Sender Name', related="company_id.mgs_golis_sender")
    mgs_golis_token = fields.Char(
        string='Golis Key', related="company_id.mgs_golis_token")
    mgs_golis_overwrite_odoo_sms = fields.Boolean(
        string='Golis Overwrite odoo sms', default=True, related="company_id.mgs_golis_overwrite_odoo_sms")

    # @api.model
    # def set_values(self):
    #     res = super(ResConfigSettings, self).set_values()
    #     self.env['ir.config_parameter'].sudo().set_param(
    #         'mgs_sms_integration.username', self.mgs_username)
    #     self.env['ir.config_parameter'].sudo().set_param(
    #         'mgs_sms_integration.password', self.mgs_password)
    #     self.env['ir.config_parameter'].sudo().set_param(
    #         'mgs_sms_integration.sender', self.mgs_sender)
    #     self.env['ir.config_parameter'].sudo().set_param(
    #         'mgs_sms_integration.key', self.mgs_key)
