# -*- coding: utf-8 -*-

from openerp import netsvc
from openerp.osv import orm, fields
from openerp.tools.translate import _


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
            if so_line.percent_invoiced == 100.0:
                continue
            val = {
                'sale_order_line_id': so_line.id,
                'percent_to_invoice': 100.0 - so_line.percent_invoiced,
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
        invoice_obj = self.pool['account.invoice']
        invoice_line_obj = self.pool['account.invoice.line']
        wf_service = netsvc.LocalService('workflow')

        sale = self._get_sale(cr, uid, context)

        invoice_vals = self._prepare_invoice_vals(
            cr, uid, sale, context=context
        )
        invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
        sale.write({
            'invoice_ids': [(4, invoice_id)],
            'invoice_with_percent': True,
        })

        wizard = self.browse(cr, uid, ids[0], context=context)
        for wizard_line in wizard.line_ids:
            if wizard_line.percent_to_invoice == 0.0:
                continue
            if wizard_line.percent_to_invoice < 0.0:
                raise orm.except_orm(_('Wrong ratio to invoice'), _(
                    'You cannot enter a negative number as the ratio to '
                    'invoice'
                ))
            if wizard_line.percent_to_invoice > (
                    100.0 - wizard_line.percent_invoiced):
                raise orm.except_orm(_('Wrong ratio to invoice'), _(
                    'You cannot enter a ratio greater than the ratio left to '
                    'invoice'
                ))
            invoice_line = self._prepare_invoice_line_vals(
                cr, uid, wizard_line, context=context
            )
            invoice_line['invoice_id'] = invoice_id
            line_id = invoice_line_obj.create(
                cr, uid, invoice_line, context=context
            )
            wizard_line.sale_order_line_id.write({
                'invoice_lines': [(4, line_id)]
            })
        invoice_obj.button_reset_taxes(cr, uid, [invoice_id], context=context)
        sale = self._get_sale(cr, uid, context)
        if all(line.percent_invoiced == 100.0 for line in sale.order_line):
            wf_service.trg_validate(
                uid, 'sale.order', sale.id, 'manual_invoice', cr
            )
            sale.write({'state': 'progress'})

        form_id = self._get_account_invoice_form_id(cr, uid, context=context)
        return {
            'name': _('Advance Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'res_id': invoice_id,
            'view_id': False,
            'views': [(form_id, 'form')],
            'context': "{'type': 'out_invoice'}",
            'type': 'ir.actions.act_window',
        }

    def _get_sale(self, cr, uid, context=None):
        if context is None:
            context = {}

        sale_obj = self.pool['sale.order']

        sale_ids = context.get('active_ids', [])
        return sale_obj.browse(cr, uid, sale_ids[0], context=context)

    def _get_account_invoice_form_id(self, cr, uid, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(
            cr, uid, 'account', 'invoice_form'
        )
        return form_res and form_res[1] or False

    def _prepare_invoice_vals(self, cr, uid, sale, context=None):
        return {
            'name': sale.client_order_ref or sale.name,
            'origin': sale.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': sale.partner_id.property_account_receivable.id,
            'partner_id': sale.partner_invoice_id.id,
            'currency_id': sale.pricelist_id.currency_id.id,
            'comment': '',
            'payment_term': sale.payment_term.id,
            'fiscal_position': (
                sale.fiscal_position.id or
                sale.partner_id.property_account_position.id
            ),
        }

    def _prepare_invoice_line_vals(self, cr, uid, wizard_line, context=None):
        so_line = wizard_line.sale_order_line_id
        sale = so_line.order_id
        inv_line_obj = self.pool['account.invoice.line']
        val = inv_line_obj.product_id_change(
            cr, uid, [],
            so_line.product_id.id,
            uom_id=so_line.product_uom.id,
            partner_id=sale.partner_id.id,
            fposition_id=sale.fiscal_position.id
        )
        res = val['value']
        tax_ids = [tax.id for tax in so_line.tax_id]
        return {
            'name': res.get('name'),
            'origin': sale.name,
            'account_id': res['account_id'],
            'price_unit': so_line.price_unit,
            'quantity': so_line.product_uos_qty,
            'discount': so_line.discount,
            'uos_id': res.get('uos_id', False),
            'product_id': so_line.product_id.id,
            'invoice_line_tax_id': [(6, 0, tax_ids)],
            'account_analytic_id': sale.project_id.id or False,
            'percent': wizard_line.percent_to_invoice,
        }


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
        'percent_invoiced': fields.related(
            'sale_order_line_id',
            'percent_invoiced',
            type='float',
            string="Invoiced (%)",
            readonly=True
        ),
        'percent_to_invoice': fields.float('To invoice (%)'),
    }
