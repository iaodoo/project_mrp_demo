# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    so_double_validation = fields.Selection([
        ('one_step', 'Confirm sale orders in one step'),
        ('two_step', 'Get 2 levels of approvals to confirm a sale order')
    ], string="SO Levels of Approvals", default='one_step',
        help="Provide a double validation mechanism for sale")

    so_double_validation_amount = fields.Monetary(
        string='Sale Double validation amount', default=0,
        help="Minimum amount for which a sale double validation is required")
