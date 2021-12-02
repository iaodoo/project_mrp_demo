# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api


class ProjectSize(models.Model):
    _name = "project.size"
    _description = "Project Type"
    _order = 'sequence'

    name = fields.Char(string="Name")
    sequence = fields.Integer(string="Sequence")
    project_process_ids = fields.One2many(
        'process.process', 'project_size_id', string="Project Process", copy=False)
