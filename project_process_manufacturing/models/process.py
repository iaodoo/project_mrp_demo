# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models


class Process(models.Model):
    _name = 'process.process'
    _description = 'Process'

    name = fields.Char('Process', copy=False)
    project_size_id = fields.Many2one('project.size', string="Project Type",
                                      help="Project Type  details in Project Process")
    is_manufacturing = fields.Boolean("Is  Manufacturing", copy=False)
    is_procurement = fields.Boolean("Is  Procurement", copy=False)
    is_approval = fields.Boolean("Is  Approval", copy=False)
    is_sample = fields.Boolean("Is Sample Order", copy=False)
    is_service = fields.Boolean("Is Service", copy=False)
    product_id = fields.Many2one('product.product', string="Service Product",
        help="Service Product To link with Sale order")
    need_customer_feedback = fields.Boolean(
        'Need Customer Feedback', copy=False)

    sequence = fields.Integer('Sequence', copy=False)
    user_id = fields.Many2one('res.users', string='Assignee', copy=False)
    is_internal_approval = fields.Boolean(string="Internal Approval")
    task_validity_days = fields.Integer(
        string='Task validity days',
        required=False,
        readonly=False,
        index=False,
        default=0,
        help=False
    )
    add_follower = fields.Boolean(string="Add Follower")
    sequence_num = fields.Integer(related="sequence", string="Sequence No")
