# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, models, fields


class Partner(models.Model):
    _inherit = 'res.partner'
    _description = 'Partner'

    credit_limit = fields.Float(string="Credit Limit")

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
            This method overide to show supplier related Product.
        """
        list_partner = []
        if self._context.get('show_supplier') and \
                self._context.get('product_id'):
            for product in self.env['product.product'].\
                    browse(self._context.get('product_id')):
                for supplier in product.seller_ids:
                    list_partner.append(supplier.name.id)
            return self.browse(list_partner).name_get()
        return super(Partner, self).name_search(name, args, operator, limit)
