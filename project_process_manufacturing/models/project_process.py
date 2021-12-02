# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models


class ProjectProcess(models.Model):
    _name = 'project.process'
    _description = 'ProjectProcess Details'

    project_id = fields.Many2one('project.project', "Project")
    sale_id = fields.Many2one("sale.order", "Sale")
    sale_order_line_id = fields.Many2one("sale.order.line", "Sale Order Line")
    process_id = fields.Many2one('mrp.routing.workcenter', "Process")
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure', default=lambda self: self.env.ref('uom.product_uom_meter').id)
    quantity = fields.Float(
        "Quantity", readonly=0)
    cost = fields.Float("Cost")
    total_process = fields.Float("Total Cost",
                                 compute='_get_used_quantity')
    sale_price = fields.Float(string="Sale Price", default=1)
    total_sale_price = fields.Float(compute='_get_total_sale_price',
                                    string="Total Sale Price")
    used_process = fields.Float("Used", compute='_get_used_quantity')
    remaining_process = fields.Float("Remaining",
                                     compute='_get_used_quantity')
    routing_id = fields.Many2one("mrp.routing",string="Routing")
    
    def _get_total_sale_price(self):
        for rec in self:
            rec.total_sale_price = rec.sale_price * rec.used_process

    def _get_used_quantity(self):
        mrp_obj = self.env['mrp.production']
        for rec in self:
            qty_done = 0.0
            mrp_recs = mrp_obj.search([('task_id.project_id', '=', rec.project_id.id), ('product_id', '=', rec.product_id.id)])
            for mrp_rec in mrp_recs:
                qty_done = sum([line.quantity_done for line in mrp_rec.move_raw_ids])
            rec.used_process = qty_done
            rec.total_process = qty_done * rec.cost
            rec.remaining_process = rec.quantity - rec.used_process

    @api.model
    def create(self, vals):
        """
        create Process in main sale order when any  Process \
        added to Project"""
        ctx = dict(self._context)
        sale_new_id = vals.get('sale_id')
        if 'project_id' in vals.keys():
            project_id = self.env['project.project'].browse(
                vals.get('project_id'))
            sale_id = project_id.sale_project_id.id
            vals.update({'sale_id': sale_id})
        if 'created_from' in ctx.keys() and ctx.get('created_from') == 'sale':
            if sale_new_id != False:
                vals.update({'sale_id': sale_new_id})
        return super(ProjectProcess, self).create(vals)

    def write(self, vals):
        """
        Update Process in main sale order when any  Process\
        update to Project"""
        if 'project_id' in vals.keys():
            project_id = self.env['project.project'].browse(
                vals.get('project_id'))
            sale_id = project_id.sale_project_id.id
            vals.update({'sale_id': sale_id})
        return super(ProjectProcess, self).write(vals)

    @api.onchange('product_id')
    def change_product_id(self):
        if not self.product_id:
            return
        product_id = self.product_id
        self.product_uom_id = product_id.uom_id