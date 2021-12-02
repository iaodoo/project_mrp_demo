# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2019 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    routing_id = fields.Many2one('mrp.routing', 'Routing')
