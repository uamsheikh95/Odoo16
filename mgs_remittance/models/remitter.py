from odoo import models, fields, api


class MGSRemittanceRemitter(models.Model):
    _name = 'mgs_remittance.remitter'
    _description = 'MGS Remittance Remitter'
    _inherit = ['mail.thread']

    name = fields.Char('Name', required=True)
    mobile = fields.Char(string="Mobile", required=True)
    email = fields.Char(string="Email")
    country_id = fields.Many2one(
        'res.country', string="Country", required=True)
    city_id = fields.Many2one(
        'mgs_remittance.city', string="City", required=True)
    id_no = fields.Char(string="Identity No.")
    guarantor = fields.Char(string='Guarantor', help="Damiin")

    transaction_line_ids = fields.One2many(
        'mgs_remittance.transaction.line', 'sender_id', string="Transaction")
