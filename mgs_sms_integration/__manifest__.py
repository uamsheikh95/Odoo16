# -*- coding: utf-8 -*-
{
    'name': "mgs_sms_integration",
    'summary': "",
    'description': "MGS SMS Integration",
    'author': "Meisour GS",
    'website': "https://www.meisour.com",
    'category': 'sms',
    'version': '0.1',
    'depends': ['base', 'account', 'stock'],
    'data': [
        'views/views.xml',
        'views/mgs_sms.xml',
        'security/ir.model.access.csv'
        ]
}
