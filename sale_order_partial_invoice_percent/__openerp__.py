# -*- coding: utf-8 -*-
{
    'name': 'Sale Partial Invoice Percent',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
        Allow to partialy invoice Sale Order lines, based on percent
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'license': 'AGPL-3',
    'depends': ['sale', 'account', 'sale_stock'],
    'data': [
        'views/sale_view.xml',
        'views/invoice_view.xml',
        'wizard/sale_view.xml',
    ],
    'test': [],
    'demo': [],
    'installable': True,
    'active': True,
}
