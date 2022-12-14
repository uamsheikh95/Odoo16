# -*- coding: utf-8 -*-
{
    'name': "MGS Purchase Reports",
    'summary': """""",
    'description': """Meisour Purchase Reports""",
    'author': "Meisour Global Solutions",
    'website': "http://www.meisour.com",
    'category': 'Reporting',
    'version': '13.01',
    'depends': ['purchase'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/paperformat.xml',
        'views/report_purchases_by_vendor.xml',
        'views/report_purchases_by_item.xml',
        'wizards/purchases_by_vendor.xml',
        'wizards/purchases_by_item.xml',
    ],
}
