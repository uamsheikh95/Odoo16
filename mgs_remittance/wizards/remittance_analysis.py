# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MgsRemittanceRemittanceAnalysis(models.TransientModel):
    _name = 'mgs_remittance.remittance_analysis'
    _description = 'Mgs Remittance Remittance Analysis'

    source_company_company_id = fields.Many2one(
        'res.company', string='From Agent', default=lambda self: self.env.company.id, required=True)
    destination_company_partner_id = fields.Many2one(
        'res.partner', string='To Agent', index=True)

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='ToDate')

    sender_id = fields.Many2one(
        'mgs_remittance.remitter', string='Remitter')
    beneficiary_id = fields.Many2one(
        'mgs_remittance.beneficiary', string='Beneficiary')

    @api.constrains('from_date', 'to_date')
    def _check_the_from_date_and_to(self):
        if self.to_date and self.from_date and self.to_date < self.from_date:
            raise ValidationError('''From Date should be less than To Date.''')

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'source_company_company_id': [self.source_company_company_id.id, self.source_company_company_id.name],
                'destination_company_partner_id': [self.destination_company_partner_id.id, self.destination_company_partner_id.name],
                'sender_id': [self.sender_id.id, self.sender_id.name],
                'beneficiary_id': [self.beneficiary_id.id, self.beneficiary_id.name],
                'from_date': self.from_date,
                'to_date': self.to_date
            },
        }

        return self.env.ref('mgs_remittance.action_remittance_analysis_report').report_action(self, data=data)


class MgsRemittanceAnalysisReport(models.AbstractModel):
    _name = 'report.mgs_remittance.remittance_analysis_report'
    _description = 'Mgs Remittance Remittance Analysis Report'

    def _lines(self, source_company_company_id, destination_company_partner_id, sender_id, beneficiary_id, from_date, to_date):
        params = []
        query = """
        SELECT mrt.date AS send_date, mrtl.id AS rid, source.name AS source_branch,
        dest.name AS destination_branch, mrr.name AS sender_name, mrb.name AS beneficiary_name,
        COALESCE(mrtl.amount, 0) AS amount, COALESCE(mrtl2.amount_due, 0) AS amount_due
        FROM mgs_remittance_transaction_line mrtl
        LEFT JOIN mgs_remittance_transaction mrt ON mrtl.transaction_id=mrt.id
        LEFT JOIN mgs_remittance_transaction_line mrtl2 ON mrtl.id=mrtl2.related_transaction_id_no
        LEFT JOIN res_partner source ON mrtl2.source_company_partner_id = source.id
        LEFT JOIN res_partner dest ON mrtl.destination_company_partner_id = dest.id
        LEFT JOIN mgs_remittance_remitter mrr ON mrtl2.sender_id=mrr.id
        LEFT JOIN mgs_remittance_beneficiary mrb ON mrtl.beneficiary_id=mrb.id
        WHERE mrtl.id IS NOT NULL
        """

        if source_company_company_id:
            params.append(source_company_company_id)
            query += " AND mrt.company_id = %s"

        if destination_company_partner_id:
            params.append(destination_company_partner_id)
            query += " AND mrtl.destination_company_partner_id = %s"

        if sender_id:
            params.append(sender_id)
            query += " AND mrt.sender_id = %s"

        if beneficiary_id:
            params.append(beneficiary_id)
            query += " AND mrtl.beneficiary_id = %s"

        if from_date:
            params.append(from_date)
            query += " AND mrt.date >= %s"

        if to_date:
            params.append(to_date)
            query += " AND mrt.to_date <= %s"

        query += " ORDER BY mrt.date, mrt.id, mrt.date"
        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'source_company_company_id': self.env['res.company'].search([('id', '=', data['form']['source_company_company_id'][0])]),
            'destination_company_partner_id': data['form']['destination_company_partner_id'],
            'sender_id': data['form']['sender_id'],
            'beneficiary_id': data['form']['beneficiary_id'],
            'from_date': data['form']['from_date'],
            'to_date': data['form']['to_date'],
            'lines': self._lines,
        }
