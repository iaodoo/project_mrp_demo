# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, api
from odoo.exceptions import ValidationError


class ProductTemplateAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"

    def write(self, vals):
        """
        Override write function which raise Validation when remove value from
        line which used in product variants.
        :param vals:
        :return:
        """
        for rec in self:
            if 'value_ids' in vals:
                for attr_value in rec.value_ids:
                    if attr_value.id not in vals['value_ids'][0][
                        2] and rec.product_tmpl_id.product_variant_ids:
                        variant_attribute_values = self.product_tmpl_id.product_variant_ids.mapped(
                            'product_template_attribute_value_ids')
                        remain_attribute_values = rec.product_template_value_ids.filtered(
                            lambda l: l.id in variant_attribute_values.ids)
                        if remain_attribute_values and \
                                attr_value in remain_attribute_values.mapped(
                            'product_attribute_value_id'):
                            raise ValidationError(
                                "You cannot remove %s values from related variant. because it is used in product variants!" % (
                                    attr_value.name))
        return super(ProductTemplateAttributeLine, self).write(vals)

    def unlink(self):
        """
        Override the unlink function which is raise Validation when remove
        attribute and values which is used in product variants.
        :return:
        """
        for rec in self:
            if rec.product_tmpl_id.product_variant_ids:
                variant_attribute_lines = rec.product_tmpl_id.product_variant_ids.mapped(
                    'product_template_attribute_value_ids').mapped('attribute_line_id')
                if variant_attribute_lines and rec in variant_attribute_lines:
                    raise ValidationError(
                        "You cannot remove attribute line %s because it is used in product variants!" % (
                            rec.attribute_id.name))
        return super(ProductTemplateAttributeLine, self).unlink()
