# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'
    _description = 'Work Center'

    user_id = fields.Many2one('res.users', string="Responsible User")
