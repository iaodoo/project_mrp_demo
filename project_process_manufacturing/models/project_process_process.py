# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models


class Processproject(models.Model):
    _name = 'project.process.process'
    _description = 'Project Process'

    project_id = fields.Many2one(
        'project.project', string="Project", copy=False)
    process_id = fields.Many2one('process.process', string="Process")
    project_size_id = fields.Many2one(related='process_id.project_size_id',
                                      string="Project Type", copy=False,
                                      help="Project Type details in Project Process")
    is_manufacturing = fields.Boolean(
        "Is  Manufacturing", related="process_id.is_manufacturing", copy=False)
    is_approval = fields.Boolean("Is  Approval",
                                 related="process_id.is_approval",
                                 copy=False)
    is_sample = fields.Boolean("Is Sample Order",
                               related="process_id.is_sample",
                               copy=False)
    task_id = fields.Many2one('project.task', string="Task", copy=False)

    stage_id = fields.Many2one('project.task.type',
                               related='task_id.stage_id', copy=False)
    user_id = fields.Many2one('res.users', copy=False, string='Assignee')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
