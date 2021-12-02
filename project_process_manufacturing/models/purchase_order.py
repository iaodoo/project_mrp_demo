# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    _description = "Purchase Order"

    task_id = fields.Many2one(
        'project.task', string="Task Details", copy=False)
    project_id = fields.Many2one("project.project",
                                 related='task_id.project_id',
                                 string="Project", copy=False)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order.line"

    part_number = fields.Char(string="Component Part Number")