# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MGSRemittanceCity(models.Model):
    _name = 'mgs_remittance.city'
    _description = 'MGS Remittance City'

    name = fields.Char('City Name', required=True, copy=False)
