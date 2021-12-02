# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    routing_ids = fields.Many2many('mrp.routing', string="Routings")
    raw_material_count = fields.Integer(string="No Of Raw Material",
                                        default=1)


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Bom Volume', required=True)

    task_routing_ids = fields.Many2many(
        'mrp.routing', 'mrp_routing_bom_line', 'bom_line_id', 'task_routing_id', 'Task Routing')