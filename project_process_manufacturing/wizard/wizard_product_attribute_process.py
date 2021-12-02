# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

import itertools
from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardProductAttributeProcess(models.TransientModel):
    _name = "wizard.attribute.process"
    _description = "Wizard for product attribute process"

    process_line_ids = fields.One2many('wizard.attribute.process.line',
                                       'wizard_attribute_id',
                                       string="Attribute Process Line")
    product_template_id = fields.Many2one('product.template',
                                          string="Product Template")
    is_set_attribute = fields.Boolean(string="Set Attribute")

    process_with_pricelist = fields.Boolean(string="Process with Update Pricelist")

    create_product_ids = fields.Many2many('product.product','create_product_ids',
        string="Product Variants")

    state = fields.Selection(
        [('step1', 'Product Variant'), ('step2', 'Process Pricelist')],
        string='Status', default='step1')

    product_pricelist_id = fields.Many2one('product.pricelist',
                                           string="Product Pricelist")
    pricelist_item_ids = fields.One2many('wizard.product.pricelist.item.attribute',
                                         'wizard_attribute_id',
                                         string="Pricelist Items")
    update_pricelist_for_selected_product = fields.Boolean(string="Update Pricelist for Selected Product")
    select_create_product_ids = fields.Many2many('product.product','selected_create_product_ids',
        string="Selected Product Variants")


    @api.model
    def default_get(self, fields_list):
        """
        inherit function to set product template value.
        :param fields_list:
        :return:
        """
        res = super(WizardProductAttributeProcess, self).default_get(
            fields_list=fields_list)

        template_id = False
        if self._context.get('active_model', False) == 'product.template' and \
                self._context.get('active_id', False):
            template_id = self.env['product.template'].browse(self._context['active_id'])
        if template_id:
            res['product_template_id'] = template_id.id
        if template_id.pricelist_item_ids:
            pricelist_item_lst = []
            for item in template_id.pricelist_item_ids:
                pricelist_item_dict = {
                    'min_quantity': item.min_quantity,
                    'price': item.price
                }
                pricelist_item_lst.append((0, 0, pricelist_item_dict))
            res['product_pricelist_id'] = template_id.product_pricelist_id.id
            res['pricelist_item_ids'] = pricelist_item_lst
        return res

    @api.onchange('is_set_attribute')
    def onchange_is_set_attribute(self):
        """
        define onchange function to set attribute value in lines
        :return:
        """
        if self.is_set_attribute and self.product_template_id and \
                self.product_template_id.attribute_line_ids:
            self.process_line_ids = False
            attribute_lst = []
            for attribute in self.product_template_id.attribute_line_ids:
                attribute_dict = {
                    'product_attribute_line_id': attribute.id or False,
                }
                line_id = self.env['wizard.attribute.process.line'].create(attribute_dict)
                attribute_lst.append((4, line_id.id))
            if attribute_lst:
                self.process_line_ids = attribute_lst
            self.is_set_attribute = False

    def process_product_attribute(self):
        """
        Define method to create custom attribute which set in wizard.
        :return:
        """
        if not self.process_line_ids:
            raise UserError(
                "Please Set Attribute First!")
        if any(not process_line.custom_value_ids for process_line in self.process_line_ids):
            raise UserError(
                "Please Set All attribute value with combination!")
        variants_to_create = []
        all_variants = self.product_template_id.with_context(active_test=False).product_variant_ids.sorted('active')
        existing_variants = {
            variant.product_template_attribute_value_ids: variant for variant in all_variants
        }
        Product = self.env["product.product"]
        product_attribute_value = self.env['product.template.attribute.value']
        if self.process_line_ids:
            product_template_value_ids =  product_attribute_value.search([
                ('product_attribute_value_id','in',self.process_line_ids.mapped('custom_value_ids').ids),
                ('product_tmpl_id','=',self.product_template_id.id),
                ('attribute_id','in',self.process_line_ids.mapped('attribute_id').ids)])
            all_combinations = itertools.product(*[
                product_template_value_ids.filtered(lambda x:x.attribute_id == ptal) for ptal in product_template_value_ids.mapped('attribute_id')
            ])
            for combination_tuple in all_combinations:
                combination = self.env['product.template.attribute.value'].concat(*combination_tuple)
                if combination not in existing_variants:
                    variants_to_create.append({
                        'product_tmpl_id': self.product_template_id.id,
                        'product_template_attribute_value_ids': [(6, 0, combination.ids)],
                        'active': self.product_template_id.active,
                    })
            if variants_to_create:
                self.create_product_ids = Product.create(variants_to_create)
                if self.process_with_pricelist:
                    self.state = 'step2'
                    return {
                            'name': 'Process Product Pricelist',
                            'type': 'ir.actions.act_window',
                            'res_model': self._name,
                            'res_id': self.id,
                            'view_type': 'form',
                            'view_mode': 'form',
                            'target': 'new',
                    }

    def process_pricelist(self):
        """
        Method define to set value in product and create pricelist.item based
        on values.
        :return:
        """

        pricelist_dict = {
            'product_pricelist_id': self.product_pricelist_id.id
        }
        pricelist_item_list = []
        for item in self.pricelist_item_ids:
            pricelist_item_dict = {
                'min_quantity': item.min_quantity,
                'price': item.price
            }
            pricelist_item_list.append((0, 0, pricelist_item_dict))
            pricelist_dict['pricelist_item_ids'] = pricelist_item_list
        if self.product_template_id.pricelist_item_ids:
            self.product_template_id.pricelist_item_ids.unlink()
        self.product_template_id.write(pricelist_dict)
        product_variant_list = False
        if self.update_pricelist_for_selected_product:
            product_variant_list = self.select_create_product_ids
        else:
            product_variant_list = self.create_product_ids
        prod_pricelist_item_env = self.env['product.pricelist.item']
        price_data_lst = []
        for variant in product_variant_list:
            product_variant_description = ''
            for value in variant.product_template_attribute_value_ids:
                product_variant_description += "%s: %s," % (value.attribute_id.name, value.name)
            for item in self.product_template_id.pricelist_item_ids:
                fixed_price = item.price
                item_dict = {
                    'product_tmpl_id': self.product_template_id.id,
                    'name': self.product_template_id.name,
                    'product_id': variant.id,
                    'pricelist_id': self.product_template_id.product_pricelist_id.id,
                    'fixed_price': fixed_price,
                    'min_quantity': item.min_quantity,
                    'applied_on': '0_product_variant',
                    'product_variant_desc': product_variant_description,
                }
                price_data_lst.append(item_dict)
        for price_data in price_data_lst:
            prod_pricelist_item_env.create(price_data)


class WizardProductAttributeProcessLine(models.TransientModel):
    _name = "wizard.attribute.process.line"
    _description = "Wizard for product attribute process"

    wizard_attribute_id = fields.Many2one('wizard.attribute.process',
                                          string="Wizard Attribute")
    attribute_id = fields.Many2one('product.attribute',
                                   related="product_attribute_line_id.attribute_id",
                                   string="Attribute")
    value_ids = fields.Many2many('product.attribute.value',
                                 related="product_attribute_line_id.value_ids",
                                 string="Attribute Line Values")
    custom_value_ids = fields.Many2many('product.attribute.value', string="Attribute Values")
    product_attribute_line_id = fields.Many2one('product.template.attribute.line',
                                                string="Attribute Line")

class WizardProductPricelistItemAttribute(models.TransientModel):
    _name = "wizard.product.pricelist.item.attribute"
    _description = 'Wizard Product Pricelist Item '

    wizard_attribute_id = fields.Many2one('wizard.attribute.process',
                                          string="Wizard Attribute")
    price = fields.Float(string="Price")
    min_quantity = fields.Integer(string="Min. Quantity")