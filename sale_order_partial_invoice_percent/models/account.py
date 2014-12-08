# -*- coding: utf-8 -*-
from openerp.osv import orm, fields
import openerp.addons.decimal_precision as dp


class InvoiceLine(orm.Model):
    _inherit = 'account.invoice.line'

    def _amount_line(self, cr, uid, ids, prop, unknow_none, context):
        res = super(InvoiceLine, self)._amount_line(
            cr, uid, ids, prop, unknow_none, context
        )
        for invoice_line in self.browse(cr, uid, ids, context=context):
            res[invoice_line.id] *= invoice_line.percent / 100.0
        return res

    _columns = {
        'percent': fields.float('Ratio invoiced (%)'),
        'price_subtotal': fields.function(
            _amount_line,
            string='Amount',
            type="float",
            digits_compute=dp.get_precision('Account'),
            store=True,
        ),
    }

    _defaults = {
        'percent': 100.0,
    }
