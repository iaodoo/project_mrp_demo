# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models

class SaleorderProcess(models.Model):
    _name = 'sale.order.process'
    _description = 'Sale Order Process'

    # Project Process
    sale_id = fields.Many2one('sale.order', string="Sale Order", copy=False)
    process_id = fields.Many2one('process.process', string="Process")
    project_size_id = fields.Many2one(related='process_id.project_size_id',
                                      string="Project Type", copy=False,
                                      help="Project Type  details in Project Process")
    is_manufacturing = fields.Boolean(
        "Is  Manufacturing", related="process_id.is_manufacturing", copy=False)
    is_approval = fields.Boolean("Is  Approval",
                                 related="process_id.is_approval",
                                 copy=False)
    is_sample = fields.Boolean("Is Sample Order",
                               related="process_id.is_sample",
                               copy=False)
