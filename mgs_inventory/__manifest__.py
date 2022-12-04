# -*- coding: utf-8 -*-
{
    'name': "MGS Inventory Reports",
    'summary': """""",
    'description': """""",
    'author': "Meisour Global Solutions",
    'website': "http://www.meisour.com",
    'category': 'Reporting',
    'version': '13.01',
    'depends': ['stock', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/paperformat.xml',
        'views/report_current_stock.xml',
        'views/report_inventory_valuation_summary.xml',
        'views/report_product_moves_history.xml',
        'views/report_non_moving_items.xml',
        'wizards/current_stock.xml',
        'wizards/inventory_valuation_summary.xml',
        'wizards/product_moves_history.xml',
        'wizards/non_moving_items.xml'
    ],
}
