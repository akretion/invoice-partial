# -*- coding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import orm, fields


class SaleAdvancePaymentInv(orm.TransientModel):
    _inherit = "sale.advance.payment.inv"

    _columns = {
        'advance_payment_method': fields.selection(
            [
                ('all', 'Invoice the whole sales order'),
                ('percentage', 'Percentage'),
                ('fixed', 'Fixed price (deposit)'),
                ('lines', 'Some order lines'),
                ('lines_percent', 'Some order lines (based on percents)'),
            ],
            'What do you want to invoice?', required=True,
            help="""Use All to create the final invoice.
                  Use Percentage to invoice a percentage of the total amount.
                  Use Fixed Price to invoice a specific amound in advance.
                  Use Some Order Lines to invoice a selection of the sales
                  order lines."""
        ),
    }

    def create_partial_percent(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard_obj = self.pool['sale.order.invoice.percent']
        so_line_obj = self.pool['sale.order.line']

        sale_ids = context.get('active_ids', [])

        so_line_ids = so_line_obj.search(
            cr, uid, [('order_id', 'in', sale_ids)], context=context
        )
        so_lines = so_line_obj.browse(cr, uid, so_line_ids, context=context)
        line_values = []
        for so_line in so_lines:
            val = {
                'sale_order_line_id': so_line.id,
                'percent_to_invoice': 100.0,
                #'percent_to_invoice': 100.0 - so_line.percent_invoiced,
            }
            line_values.append((0, 0, val))
        val = {'line_ids': line_values, }
        wizard_id = wizard_obj.create(cr, uid, val, context=context)
        res = {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.invoice.percent',
            'res_id': wizard_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
        return res


class SOInvoicePercent(orm.TransientModel):
    _name = "sale.order.invoice.percent"

    _columns = {
        'line_ids': fields.one2many(
            'sale.order.invoice.percent.line',
            'wizard_id',
            string="Lines"
        ),
    }

    def create_invoice(self, cr, uid, ids, context=None):
        pass


class SOInvoicePercentLine(orm.TransientModel):
    _name = 'sale.order.invoice.percent.line'
    _columns = {
        'wizard_id': fields.many2one(
            'sale.order.invoice.percent', string='Wizard'
        ),
        'sale_order_line_id': fields.many2one(
            'sale.order.line', string='sale.order.line'
        ),
        'name': fields.related(
            'sale_order_line_id',
            'name',
            type='text',
            string="Line",
            readonly=True
        ),
        'order_qty': fields.related(
            'sale_order_line_id',
            'product_uom_qty',
            type='float',
            string="Quantity sold",
            readonly=True
        ),
        #'percent_invoiced': fields.related(
        #    'sale_order_line_id',
        #    'percent_invoiced',
        #    type='float',
        #    string="Invoiced",
        #    readonly=True
        #),
        'percent_to_invoice': fields.float('To invoice (%)'),
    }
