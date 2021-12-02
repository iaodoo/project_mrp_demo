# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    so_order_approval = fields.Boolean("Sale Order Approval",
                                       default=lambda self: self.env.user.
                                       company_id.
                                       so_double_validation == 'two_step')
    so_double_validation = fields.Selection(
        related='company_id.so_double_validation',
        string="Sale Levels of Approvals *", readonly=False)
    so_double_validation_amount = fields.Monetary(
        related='company_id.so_double_validation_amount',
        string="Sale Minimum Amount",
        currency_field='company_currency_id',
        readonly=False)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True,
                                          help='Utility field to express amount currency')

    product_variant_creation_limit = fields.Integer(
        string="Product Variant Creation Limit", default=3000)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.so_double_validation = 'two_step' if self.\
            so_order_approval else 'one_step'
        self.env['ir.config_parameter'].sudo().set_param(
            'project_process_manufacturing.product_variant_creation_limit',
            self.product_variant_creation_limit)

    @api.model
    def get_values(self):
        """
        Inherit function to get the value in configuration setting.
        :return:
        """
        res = super(ResConfigSettings, self).get_values()
        res['product_variant_creation_limit'] = int(self.env['ir.config_parameter'].sudo(
        ).get_param('project_process_manufacturing.product_variant_creation_limit',
                    False) or 3000)
        return res
