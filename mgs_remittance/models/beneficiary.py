from odoo import models, fields, api


class MGSRemittanceBeneficiary(models.Model):
    _name = 'mgs_remittance.beneficiary'
    _description = 'MGS Remittance Beneficiary'
    _inherit = ['mail.thread']
    # _inherits = {'res.partner': 'partner_id'}

    name = fields.Char('Name', required=True)
    mobile = fields.Char(string="Mobile", required=True)
    email = fields.Char(string="Email")
    country_id = fields.Many2one(
        'res.country', string="Country", required=True)
    city_id = fields.Many2one(
        'mgs_remittance.city', string="City", required=True)
    id_no = fields.Char(string="Identity No.")
    guarantor = fields.Char(string='Guarantor', help="Damiin")
    partner_id = fields.Many2one('res.partner', ondelete='restrict', auto_join=True, index=True,
                                 string='Related Partner', help='Partner-related data of the beneficiary')

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
        return super(MGSRemittanceBeneficiary, self).create(vals)
