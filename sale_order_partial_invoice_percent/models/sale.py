# -*- coding: utf-8 -*-
from openerp.osv import orm, fields


class SaleOrderLine(orm.Model):
    _inherit = "sale.order.line"

    def field_percent_invoiced(self, cr, uid, ids, field_list, arg, context):
        res = dict.fromkeys(ids, 0.0)
        for so_line in self.browse(cr, uid, ids, context=context):
            for invoice_line in so_line.invoice_lines:
                if invoice_line.percent:
                    res[so_line.id] += invoice_line.percent
                else:
                    ratio = (
                        invoice_line.price_subtotal / so_line.price_subtotal
                    )
                    res[so_line.id] += ratio * 100.0
        return res

    _columns = {
        'percent_invoiced': fields.function(
            field_percent_invoiced,
            string='Invoiced (%)',
            type='float',
            help="the quantity of product from this line already invoiced"
        ),
    }
