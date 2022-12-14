# -*- coding: utf-8 -*-
{
    'name': "MGS Accounting Reports",
    'summary': """""",
    'description': """""",
    'author': "Meisour Global Solutions",
    'website': "http://www.meisour.com",
    'category': 'Reporting',
    'version': '13.01',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/paperformat.xml',
        'views/report_invoices_by_partner.xml',
        'views/report_invoices_by_item.xml',
        'views/report_account_statement.xml',
        'views/report_gross_profit.xml',
        'views/report_invoice_detail.xml',
        'views/report_receipt_and_payment.xml',
        'wizards/invoices_by_partner.xml',
        'wizards/invoices_by_item.xml',
        'wizards/account_statement.xml',
        'wizards/gross_profit.xml',
        'wizards/invoice_detail.xml',
        'wizards/receipt_and_payment.xml'
    ],
}
