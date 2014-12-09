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


class AccountInvoiceTax(orm.Model):
    _inherit = "account.invoice.tax"

    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(
            cr, uid, invoice_id, context=context
        )
        cur = inv.currency_id
        company_currency = self.pool['res.company'].browse(
            cr, uid, inv.company_id.id
        ).currency_id.id
        for line in inv.invoice_line:
            computed_taxes = tax_obj.compute_all(
                cr, uid,
                line.invoice_line_tax_id,
                (line.price_unit * (1-(line.discount or 0.0)/100.0)),
                line.quantity * line.percent / 100.0,
                line.product_id,
                inv.partner_id
            )
            for tax in computed_taxes['taxes']:
                val = {}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = cur_obj.round(
                    cr, uid, cur,
                    tax['price_unit'] * line.quantity * line.percent / 100.0
                )

                if inv.type in ('out_invoice', 'in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(
                        cr, uid,
                        inv.currency_id.id,
                        company_currency,
                        val['base'] * tax['base_sign'],
                        context={
                            'date': inv.date_invoice or
                            fields.date.context_today(
                                self, cr, uid, context=context
                            )
                        },
                        round=False
                    )
                    val['tax_amount'] = cur_obj.compute(
                        cr, uid,
                        inv.currency_id.id,
                        company_currency,
                        val['amount'] * tax['tax_sign'],
                        context={
                            'date': inv.date_invoice or
                            fields.date.context_today(
                                self, cr, uid, context=context
                            )
                        },
                        round=False
                    )
                    val['account_id'] = (
                        tax['account_collected_id'] or line.account_id.id
                    )
                    val['account_analytic_id'] = (
                        tax['account_analytic_collected_id']
                    )
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(
                        cr, uid,
                        inv.currency_id.id,
                        company_currency,
                        val['base'] * tax['ref_base_sign'],
                        context={
                            'date': inv.date_invoice or
                            fields.date.context_today(
                                self, cr, uid, context=context
                            )
                        },
                        round=False
                    )
                    val['tax_amount'] = cur_obj.compute(
                        cr, uid,
                        inv.currency_id.id,
                        company_currency,
                        val['amount'] * tax['ref_tax_sign'],
                        context={
                            'date': inv.date_invoice or
                            fields.date.context_today(
                                self, cr, uid, context=context
                            )
                        },
                        round=False
                    )
                    val['account_id'] = (
                        tax['account_paid_id'] or line.account_id.id
                    )
                    val['account_analytic_id'] = (
                        tax['account_analytic_paid_id']
                    )

                key = (
                    val['tax_code_id'],
                    val['base_code_id'],
                    val['account_id'],
                    val['account_analytic_id']
                )
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
        return tax_grouped
