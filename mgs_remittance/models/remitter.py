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
    partner_id = fields.Many2one('res.partner', ondelete='restrict', auto_join=True, index=True,
                                 string='Related Partner', help='Partner-related data of the remitter')

    @api.model
    def create(self, vals):
        created_partner = self.env['res.partner'].create({
            'name': vals['name'],
            'mobile': vals['mobile'],
            'email': vals['email'],
            'country_id': vals['country_id'],
            'city': self.env['mgs_remittance.city'].search([('id', '=', vals['city_id'])]).name,
        })
        vals['partner_id'] = created_partner.id
        return super(MGSRemittanceRemitter, self).create(vals)
