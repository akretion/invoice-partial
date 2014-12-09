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


class SaleOrder(orm.Model):
    _inherit = 'sale.order'

    _columns = {
        'invoice_with_percent': fields.boolean('Invoice with percent'),
    }

    _defaults = {
        'invoice_with_percent': False,
    }

    def make_invoice_button(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        order = self.browse(cr, uid, ids[0], context=context)
        if order.invoice_with_percent:
            wizard = self.pool["sale.advance.payment.inv"]
            ctx = context.copy()
            ctx['active_ids'] = ids
            return wizard.create_partial_percent(cr, uid, [], context=ctx)

        ir_model_data = self.pool.get('ir.model.data')
        obj_type, obj_id = ir_model_data.get_object_reference(
            cr, uid, 'sale', 'action_view_sale_advance_payment_inv'
        )
        return self.pool[obj_type].read(cr, uid, obj_id, context=context)
