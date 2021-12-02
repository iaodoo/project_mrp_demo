# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models


class ProjectRawmaterial(models.Model):
    _name = "project.raw.material"
    _description = 'ProjectRawmaterial Details'

    product_id = fields.Many2one('product.product', "Product")
    location_id = fields.Many2one('stock.location', "Source Location")
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location")
    project_id = fields.Many2one("project.project", "Project")
    sale_id = fields.Many2one("sale.order", "Sale")
    sale_order_line_id = fields.Many2one("sale.order.line", "Sale order Line")
    qty_available = fields.Float(
        "Available Quantity", compute='_compute_available_quantities')
    square_meter = fields.Integer(string="Pieces", default=1)
    order_qty = fields.Float(string="SQM to Consume")
    used_qty = fields.Float("Used")
    remaining_qty = fields.Float("Remaining",
                                 compute='compute_remaining_qty',
                                 store=True)
    cost = fields.Float(
        "Cost", related="product_id.standard_price", readonly=0)
    total_raw_material_cost = fields.Float("Total",
                                           compute='compute_remaining_qty_total',
                                           store=True)
    dummy_finish_product_ids = fields.Many2many("product.product",
                                                string="Dummy Manufacturing Product",
                                                compute='_get_dummy_finish_product_ids', store=True)
    finished_product_id = fields.Many2one("product.product",
                                          string="Manufacturing Product")

    part_number = fields.Char(string="Component Part Number")


    @api.depends('project_id.finished_sale_line_ids')
    def _get_dummy_finish_product_ids(self):
        for rec in self:
            product_ids = rec.project_id.finished_sale_line_ids.mapped(
                'product_id')
            rec.dummy_finish_product_ids = [(6, 0, product_ids.ids)]

    @api.depends('used_qty', 'order_qty')
    def compute_remaining_qty(self):
        """ Compute the total remaining quantity."""
        for rec in self:
            rec.remaining_qty = rec.order_qty - rec.used_qty

    @api.depends('used_qty', 'order_qty', 'cost')
    def compute_remaining_qty_total(self):
        """ Compute the total remaining quantity."""
        for rec in self:
            rec.total_raw_material_cost = rec.used_qty * rec.cost

    @api.onchange('product_id')
    def _compute_available_quantities(self):
        Quant = self.env['stock.quant']
        prod_obj = self.env['product.product']
        comp_id = self.env.user.company_id
        qty_available = 0.0
        for record in self:
            prod_id = prod_obj.search([('product_tmpl_id', '=', record.product_id.product_tmpl_id.id)],
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

    @api.model
    def create(self, vals):
        """
        Create Raw Material in main sale order when any  Rawmaterial\
        added to Project.
        """
        sale_new_id = vals.get('sale_id')
        ctx = dict(self._context)
        if 'project_id' in vals.keys():
            project_id = self.env['project.project'].browse(
                vals.get('project_id'))
            sale_id = project_id.sale_project_id.id
            vals.update({'sale_id': sale_id})
        if 'created_from' in ctx.keys() and ctx.get('created_from') == 'sale':
            if sale_new_id != False:
                vals.update({'sale_id': sale_new_id})
        return super(ProjectRawmaterial, self).create(vals)

    def write(self, vals):
        """
        Update Raw Material in main sale order when any  Rawmaterial\
        Update to Project.
        """
        if 'project_id' in vals.keys():
            project_id = self.env['project.project'].browse(
                vals.get('project_id'))
            sale_id = project_id.sale_project_id.id
            vals.update({'sale_id': sale_id})
        return super(ProjectRawmaterial, self).write(vals)
