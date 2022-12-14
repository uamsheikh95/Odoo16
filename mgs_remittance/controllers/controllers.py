# -*- coding: utf-8 -*-
# from odoo import http


# class MgsRemittance(http.Controller):
#     @http.route('/mgs_remittance/mgs_remittance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mgs_remittance/mgs_remittance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mgs_remittance.listing', {
#             'root': '/mgs_remittance/mgs_remittance',
#             'objects': http.request.env['mgs_remittance.mgs_remittance'].search([]),
#         })

#     @http.route('/mgs_remittance/mgs_remittance/objects/<model("mgs_remittance.mgs_remittance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mgs_remittance.object', {
#             'object': obj
#         })
