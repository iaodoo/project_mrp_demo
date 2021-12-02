# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

import itertools

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def default_get(self, fields_list):
        """
        Inherit the function to set default value in product
        :param fields_list:
        :return:
        """
        res = super(ProductTemplate, self).default_get(fields_list=fields_list)
        res['type'] = 'product'
        res['invoice_policy'] = 'delivery'
        res['tracking'] = 'lot'
        return res

    @api.onchange('type')
    def onchange_product_type(self):
        """
        Define the method to change tracking based on product type.
        :return:
        """
        if self.type == 'service':
            self.tracking = 'none'


    def _create_variant_ids(self):
        """
        Inherit function to set the variant creation limit.
        :return:
        """
        variant_creation_limit = int(self.env[
            'ir.config_parameter'].sudo().get_param(
            'project_process_manufacturing.product_variant_creation_limit', False))
        if variant_creation_limit > 1000:
            self.flush()
            Product = self.env["product.product"]
    
            variants_to_create = []
            variants_to_activate = Product
            variants_to_unlink = Product
    
            for tmpl_id in self:
                lines_without_no_variants = tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes()
    
                all_variants = tmpl_id.with_context(active_test=False).product_variant_ids.sorted('active')
    
                current_variants_to_create = []
                current_variants_to_activate = Product

    
                # adding an attribute with only one value should not recreate product
                # write this attribute on every product to make sure we don't lose them
                single_value_lines = lines_without_no_variants.filtered(lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
                if single_value_lines:
                    for variant in all_variants:
                        combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()
                        # Do not add single value if the resulting combination would
                        # be invalid anyway.
                        if (
                            len(combination) == len(lines_without_no_variants) and
                            combination.attribute_line_id == lines_without_no_variants
                        ):
                            variant.product_template_attribute_value_ids = combination
                # allow to add attribute value in existing variant
                for variant in all_variants:
                    for line in lines_without_no_variants:
                        exist = False
                        for attribute in line.product_template_value_ids:
                            if attribute in variant.product_template_attribute_value_ids:
                                exist = True
                        if not exist:
                            combination = variant.product_template_attribute_value_ids | line.product_template_value_ids._only_active()[0]
                            variant.product_template_attribute_value_ids = combination

                # Determine which product variants need to be created based on the attribute
                # configuration. If any attribute is set to generate variants dynamically, skip the
                # process.
                # Technical note: if there is no attribute, a variant is still created because
                # 'not any([])' and 'set([]) not in set([])' are True.

                if not tmpl_id.has_dynamic_attributes():
                    # Iterator containing all possible `product.template.attribute.value` combination
                    # The iterator is used to avoid MemoryError in case of a huge number of combination.
                    all_combinations = itertools.product(*[
                        ptal.product_template_value_ids._only_active() for ptal in lines_without_no_variants
                    ])
                    # Set containing existing `product.template.attribute.value` combination
                    existing_variants = {
                        variant.product_template_attribute_value_ids: variant for variant in all_variants
                    }
                    # For each possible variant, create if it doesn't exist yet.
                    for combination_tuple in all_combinations:
                        combination = self.env['product.template.attribute.value'].concat(*combination_tuple)
                        if combination in existing_variants:
                            current_variants_to_activate += existing_variants[combination]
                        else:
                            current_variants_to_create.append({
                                'product_tmpl_id': tmpl_id.id,
                                'product_template_attribute_value_ids': [(6, 0, combination.ids)],
                                'active': tmpl_id.active,
                            })
                            if len(current_variants_to_create) > variant_creation_limit:
                                raise UserError(_(
                                    'The number of variants to generate is too high. '
                                    'You should either not generate variants for each combination or generate them on demand from the sales order. '
                                    'To do so, open the form view of attributes and change the mode of *Create Variants*.'))
                    variants_to_create += current_variants_to_create
                    variants_to_activate += current_variants_to_activate
                    # only allow to unlink on dynamic attribute
                    variants_to_unlink += all_variants - current_variants_to_activate
    
            if variants_to_activate:
                variants_to_activate.write({'active': True})
            if variants_to_create:
                Product.create(variants_to_create)
            if variants_to_unlink:
                variants_to_unlink._unlink_or_archive()
    
            # prefetched o2m have to be reloaded (because of active_test)
            # (eg. product.template: product_variant_ids)
            # We can't rely on existing invalidate_cache because of the savepoint
            # in _unlink_or_archive.
            self.flush()
            self.invalidate_cache()
            return True
        else:
            return super(ProductTemplate, self)._create_variant_ids()
