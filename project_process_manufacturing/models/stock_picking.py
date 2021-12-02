# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class Picking(models.Model):
    _inherit = 'stock.picking'
    _description = "Transfer"

    sale_type = fields.Selection([
        ('direct', 'Direct'), ('supply', 'Supply'),
        ('supply_install', 'Supply & Install')
    ], help="Sale Type is used  for type of sale in Transfer")
    project_size_id = fields.Many2one('project.size', string="Project Type",
                                      help="Project Type details in Transfer")
