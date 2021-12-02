# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, models, fields
from odoo.exceptions import Warning, UserError, ValidationError


class CreateProductionWizard(models.TransientModel):
    _name = 'create.production.wizard'
    _description = 'Create production wizard'

    task_id = fields.Many2one('project.task', string="Project")
    line_ids = fields.One2many(
        'production.wizard.line', 'wizard_id', string="Finish Product Lines")
    component_line_ids = fields.One2many(
        'production.component.line', 'wizard_id', string="Component Product Lines")

    is_manufacturing = fields.Boolean(
        "Show Manufacturing", related='task_id.is_manufacturing')
    is_service = fields.Boolean(
        "Show Service", related="task_id.is_service")

    mail_date = fields.Date(
        string='Mail Date'
    )
    # New routing changes functionality
    is_change_routing = fields.Boolean(string="Want to change Routing")
    is_change_raw_material = fields.Boolean(string="Want to change Raw Material")

    @api.onchange('line_ids')
    def onchange_line_ids(self):
        if self.line_ids.filtered(lambda p: p.create_mo):
            if not self.component_line_ids:
                sale_order_line_id = self.line_ids.filtered(lambda p: p.create_mo).sale_order_line_id
                vals_list = []
                if self.task_id.project_id.raw_material_line_ids:
                    for bom in  self.task_id.project_id.raw_material_line_ids.filtered(
                            lambda p: p.sale_order_line_id == sale_order_line_id):
                        process_bom = False
                        vals_dict = {'product_id': bom.finished_product_id.id,
                                     'component_product_id': bom.product_id.id,
                                     'part_number': bom.part_number}
                        # new routing id setup code to set routing in wizard
                        routing_id = False
                        # if bom.product_id.routing_id:
                        #     routing_id = bom.product_id.routing_id
                        # if not routing_id:
                        bom_id = self.env['mrp.bom'].search([
                            ('product_tmpl_id', '=',bom.product_id.product_tmpl_id.id)],
                            limit=1)
                        if bom_id and bom_id.routing_id:
                            routing_id = bom_id.routing_id
                        vals_dict.update(
                            {'change_routing_id': routing_id and routing_id.id or False})
                        if routing_id:
                            vals_dict.update({'is_add_routing': True})
                        if bom.product_id.bom_ids:
                            bom_id = bom.product_id.bom_ids[0]
                            vals_dict.update({'routing_ids': bom_id.routing_ids.ids})
                            if bom_id and bom_id.bom_line_ids.mapped('task_routing_ids'):
                                process_bom = True
                                material_count = self.env['mrp.bom.line'].search_count([
                                    ('task_routing_ids', '=', False),
                                    ('id', 'in', bom_id.bom_line_ids.ids)
                                ])
                                exact_bom_line = self.env['mrp.bom.line']
                                for current_line in bom_id.bom_line_ids:
                                    if not current_line._skip_bom_line(bom.product_id):
                                        exact_bom_line += current_line
                                if exact_bom_line.mapped('task_routing_ids') and routing_id not in exact_bom_line.mapped('task_routing_ids'):
                                    routing_id = exact_bom_line.mapped('task_routing_ids')[0]
                                for bom_line in self.env['mrp.bom.line'].search([
                                    ('task_routing_ids', '=', routing_id.id),
                                    ('id', 'in', exact_bom_line.ids)], limit=bom_id.raw_material_count - material_count):
                                    vals_dict = {
                                        'product_id': bom.finished_product_id.id,
                                        'component_product_id': bom.product_id.id,
                                        'part_number': bom.part_number,
                                        'change_routing_id': routing_id and routing_id.id or False,
                                        'product_ids': [(6, 0, exact_bom_line.mapped('product_id').ids)],
                                        'routing_ids': [(6, 0,exact_bom_line.mapped('task_routing_ids').ids)],
                                        'bom_id': bom_id.id,
                                        'material_product_id': bom_line.product_id.id or False
                                    }
                                    if routing_id:
                                        vals_dict.update({'is_add_routing': True})
                                    if bom_line.product_id:
                                        vals_dict.update({'is_add_material_product': True})
                                    vals_list.append((0, 0, vals_dict))
                        #  here for routing set in dict
                        if not process_bom:
                            vals_list.append((0, 0, vals_dict))
                if vals_list:
                    self.component_line_ids = vals_list
        else:
            self.component_line_ids = False

    @api.onchange('task_id')
    def change_task_id(self):
        if not self.task_id:
            return
        project_id = self.task_id.project_id
        manufacture_sale_order_line_ids = project_id.raw_material_line_ids.mapped(
            'sale_order_line_id')
        qty_dict = {}
        rem_qty = {}
        for order_line in project_id.finished_sale_line_ids:
            qty_dict.update({order_line.id: order_line.product_uom_qty})
            rem_qty.update(
                {order_line.id: order_line.product_uom_qty - order_line.mrp_remaining_qty_add})
        vals_list = []
        for sale_order_line in manufacture_sale_order_line_ids:
            vals_dict = {'product_id': sale_order_line.product_id.id,
                         'create_mo': False,
                         'sale_order_line_id': sale_order_line.id,
                         'remaining_qty_to_produce': rem_qty.get(sale_order_line.id),
                         'ordered_qty': qty_dict.get(sale_order_line.id)}

            # new routing id setup code to set routing in wizard
            routing_id = False
            # if sale_order_line.product_id.routing_id:
            #     routing_id = sale_order_line.product_id.routing_id
            # if not routing_id:
            bom_id = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', sale_order_line.product_id.product_tmpl_id.id)], limit=1)
            if bom_id and bom_id.routing_id:
                routing_id = bom_id.routing_id
            vals_dict.update({'change_routing_id': routing_id and routing_id.id or False})
            if sale_order_line.product_id.bom_ids:
                bom_id = sale_order_line.product_id.bom_ids[0]
                vals_dict.update({'routing_ids': bom_id.routing_ids.ids})
            #  here for routing set in dict
            vals_list.append((0, 0, vals_dict))
        self.line_ids = vals_list

    def action_create_production(self):
        if not self.line_ids:
            return False
        else:
            if self.component_line_ids:
                for component in self.component_line_ids.filtered(lambda x: x.bom_id):
                    bom_line = component.bom_id.bom_line_ids.filtered(
                        lambda l: l.product_id == component.material_product_id and \
                                  component.change_routing_id in l.task_routing_ids)
                    if not bom_line:
                        raise ValidationError("The %s Routing and %s Raw material is not exist in Bills of material!"
                                              %(component.change_routing_id.name, component.material_product_id.name))
                    same_component = self.component_line_ids.filtered(
                        lambda l: l.component_product_id == component.component_product_id)
                    if same_component.mapped('change_routing_id') and len(
                            same_component.mapped('change_routing_id')) > 1:
                        raise ValidationError("The %s Component should have same Routing!"
                                              %(component.component_product_id.name))
            create_mo_line = self.line_ids.filtered(
                lambda self: self.create_mo == True)
            qty_dict = {}
            if not create_mo_line:
                raise UserError(
                    "Please select any product to create manufacturing order!")
            if create_mo_line.quantity <= 0:
                raise UserError(
                    "The quantity to produce must be positive!")
            qty_dict.update({create_mo_line.sale_order_line_id.id: create_mo_line.quantity})
            # for line in self.line_ids:
            #     if line.sale_order_line_id.id not in qty_dict.keys():
            #         qty_dict.update({line.sale_order_line_id.id: line.quantity})
            # project_id = self.task_id.project_id
            # for order_line in project_id.finished_sale_line_ids:
            #     if order_line.id in qty_dict.keys():
            #         order_line.mrp_remaining_qty_add = order_line.mrp_remaining_qty_add + \
            #             qty_dict.get(order_line.id)
            create_mo_line.sale_order_line_id.mrp_remaining_qty_add += create_mo_line.quantity

            # Routing write in product from set in finished product line and
            # component line
            if create_mo_line.change_routing_id:
                create_mo_line.sale_order_line_id.product_id.write(
                    {'routing_id': create_mo_line.change_routing_id.id or False})
            if self.component_line_ids:
                products = self.env['product.product']
                for component_line in self.component_line_ids:
                    if component_line.component_product_id and \
                            component_line.change_routing_id and component_line.component_product_id not in products:
                        component_line.component_product_id.write(
                            {'routing_id': component_line.change_routing_id.id or False})
                        products += component_line.component_product_id
            # set the routing in product

            production_id =  self.task_id.with_context(
                {'sale_order_line_for_mo': create_mo_line.sale_order_line_id, 'quantity': qty_dict}).create_production_order()
            if production_id and not production_id.production_material_line_ids and self.component_line_ids:
                material_lst = []
                for component in self.component_line_ids.filtered(lambda l: l.material_product_id):
                    material_dict = {
                        'material_product_id': component.material_product_id.id or False,
                        'routing_id': component.change_routing_id and component.change_routing_id.id or False,
                        'component_product_id': component.component_product_id and component.component_product_id.id or False
                    }
                    material_lst.append((0, 0, material_dict))
                production_id.write({'production_material_line_ids': material_lst})
            return production_id

    def process_sub_task_only(self):
        return True


class ProductComponentLine(models.TransientModel):
    _name = 'production.component.line'
    _description = 'Production Component line'


    wizard_id = fields.Many2one(
        'create.production.wizard', string="Create Production Wizard")
    part_number = fields.Char(string="Component Part Number")

    product_id = fields.Many2one('product.product', string="Product")
    component_product_id = fields.Many2one('product.product', string="Component Product")

    # new routing changes functionality
    is_change_routing = fields.Boolean(related="wizard_id.is_change_routing")
    change_routing_id = fields.Many2one('mrp.routing', string="Routing")
    bom_ids = fields.One2many(related="component_product_id.bom_ids")
    material_product_id = fields.Many2one('product.product',
                                          string="Raw Material Product")
    bom_id = fields.Many2one('mrp.bom', string="Bills Of Matreial")
    product_ids = fields.Many2many('product.product', string="Raw material Products")
    routing_ids = fields.Many2many('mrp.routing', string="Bom Line Routings")
    is_add_routing = fields.Boolean(string="Is Add Routing")
    is_add_material_product = fields.Boolean(string="Is Add Material Product")

    is_change_raw_material = fields.Boolean(related="wizard_id.is_change_raw_material")

    @api.onchange('material_product_id')
    def onchange_material_product(self):
        if self.material_product_id and self.change_routing_id:
            bom_line = self.bom_id.bom_line_ids.filtered(
                lambda l: l.product_id == self.material_product_id and  self.change_routing_id in l.task_routing_ids)
            if not bom_line:
                raise ValidationError(
                    "%s: Routing and %s: Component combination not found in %s: Bills of Material"
                    %(self.change_routing_id.name, self.material_product_id.name ,self.bom_id.product_tmpl_id.name))


class ProductionWizardLine(models.TransientModel):
    _name = 'production.wizard.line'
    _description = 'Production wizard line'

    wizard_id = fields.Many2one(
        'create.production.wizard', string="Create Production Wizard")
    product_id = fields.Many2one('product.product', string="Product")
    create_mo = fields.Boolean(string="Create MO")
    ordered_qty = fields.Float(string="Ordered Qty")
    quantity = fields.Float(string='Quantity')
    remaining_qty_to_produce = fields.Float(string='Remaining Qty to Produce')
    actual = fields.Float(string='Actual remaining')
    consume = fields.Float(string='Comsome')
    sale_order_line_id = fields.Many2one("sale.order.line", "Sale order Line")

    # routing changes functionality
    is_change_routing = fields.Boolean(related="wizard_id.is_change_routing")
    change_routing_id = fields.Many2one('mrp.routing', string="Routing")
    routing_ids = fields.Many2many('mrp.routing', string="Bom Line Routings")

    @api.onchange('quantity')
    def quantity_onchange(self):
        if self.quantity > self.remaining_qty_to_produce:
            raise Warning("Quantity Should'nt be greater then remaining.")
        if self.remaining_qty_to_produce <= 0:
            self.remaining_qty_to_produce = self.ordered_qty - self.quantity

    @api.onchange('create_mo')
    def onchange_create_mo(self):
        """
        Define onchange method to check create_mo boolean not select in
        multiple line.
        :return:
        """
        already_exist_create_mo = self.wizard_id.line_ids.filtered(
            lambda l: l.create_mo == True and l.sale_order_line_id != self.sale_order_line_id)
        if already_exist_create_mo:
            raise UserError("You cannot select Create MO in multiple line!")