# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, api


class ProcurementRawMaterial(models.TransientModel):
    _name = 'procurement.raw.material'
    _description = 'ProcurementRawMaterial'

    product_id = fields.Many2one("product.product", string="Product")
    partner_id = fields.Many2one("res.partner", string="Partner")
    procurement_request_id = fields.Many2one("procurement.order.request",
                                             string="Procurement Request")
    qty_available = fields.Float(
        "Available Quantity", compute='_compute_available_quantities')
    order_qty = fields.Float("Order Quantity")
    cost = fields.Float(
        "Cost", related="product_id.standard_price", readonly=0)

    @api.onchange('product_id')
    @api.depends('procurement_request_id')
    def _compute_available_quantities(self):
        """
            This method throguh check Availabel Quantity
            in Product and also set seller.
        """
        Quant = self.env['stock.quant']
        prod_obj = self.env['product.product']
        comp_id = self.env.user.company_id
        qty_available = 0.0
        for record in self:
            if record.product_id and \
                    record.product_id.seller_ids:
                record.partner_id = record.product_id.seller_ids.mapped('name')[
                    0].id
            else:
                record.partner_id = False
            prod_id = prod_obj.search(
                [('product_tmpl_id', '=', record.product_id.product_tmpl_id.id)],
                limit=1)
            if prod_id and comp_id:
                domain_quant = [
                    ('product_id', '=', prod_id.id),
                    ('company_id', '=', comp_id.id),
                ]
                quants_res = dict((item['product_id'][0], item['quantity'] - item['reserved_quantity'])
                                  for item in Quant.read_group(domain_quant,
                                                               ['product_id', 'quantity', 'reserved_quantity'], [
                                                                   'product_id'],
                                                               orderby='id')
                                  )
                qty_available = quants_res.get(prod_id.id, 0.0)
            record.qty_available = qty_available
