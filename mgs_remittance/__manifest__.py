# -*- coding: utf-8 -*-
{
    'name': "MGS Remittance",

    'summary': """
        """,

    'description': """
       
    """,

    'author': "Meisour GS",
    'website': "http://www.meisour.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Finance',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],
    'license': 'LGPL-3',

    # always loaded
    'data': [
        'security/security.xml',
        'data/remittance_data.xml',
        'security/ir.model.access.csv',
        'views/remitter.xml',
        'views/beneficiary.xml',
        'views/city.xml',
        'views/res_config.xml',
        'views/send_remittance_receipt.xml',
        'views/payout_voucher.xml',
        'views/report_remittance_analysis.xml',
        'views/report_remittance_payments.xml',
        'wizards/create_payment.xml',
        'wizards/search_transaction.xml',
        'wizards/remittance_analysis.xml',
        'wizards/remittance_payments.xml',
        'views/transaction.xml',
        'views/remittance_menu.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
