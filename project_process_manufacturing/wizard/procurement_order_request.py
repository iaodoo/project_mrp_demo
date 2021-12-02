# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProcurementOrderRequest(models.TransientModel):
    _name = 'procurement.order.request'
    _description = 'ProcurementOrderRequest'

    procurement_raw_material_ids = fields.One2many(
        'procurement.raw.material',
        'procurement_request_id',
        string='Raw Material')
    project_id = fields.Many2one("project.project", string="Project")

    @api.model
    def default_get(self, fields):
        """
        This method through set Raw material and accessories
        Automatically.
        """
        result = super(ProcurementOrderRequest, self).default_get(fields)
        task_id = self.env['project.task'].browse(
            self._context.get('active_ids', []))
        raw_material_product = []
        if task_id and task_id.project_id \
                and task_id.project_id.raw_material_line_ids:
            for raw_material in task_id.project_id.raw_material_line_ids:
                raw_material_product.append((0, 0, {
                    'product_id': raw_material.product_id.id,
                    'partner_id': raw_material.product_id.seller_ids and
                    raw_material.product_id.seller_ids.mapped('name')[
                        0].id or False,
                    'order_qty': raw_material.order_qty,
                    'qty_available': 0.0,
                    'cost': raw_material.product_id.standard_price
                }))
            result.update(
                {'procurement_raw_material_ids': raw_material_product,
                 'project_id': task_id.project_id.id
                 })
        # for accessories in task_id.project_id.accessories_ids:
        #     raw_material_product.append((0, 0, {
        #         'product_id': accessories.product_id.id,
        #         'partner_id': accessories.product_id.seller_ids and
        #         accessories.product_id.seller_ids.mapped('name')[
        #             0].id or False,
        #         'order_qty': accessories.quantity,
        #         'qty_available': 0.0,
        #         'cost': accessories.product_id.standard_price
        #     }))
        #     result.update(
        #         {'procurement_raw_material_ids': raw_material_product,
        #          'project_id': task_id.project_id.id
        #          })
        return result

    def generate_purchase_order(self):
        """
         This method through generate Purchase order.
            When procurement set in task.
        """
        task_id = self.env['project.task'].browse(
            self._context.get('active_ids', []))
        picking_type_id = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming'),
             ('warehouse_id.company_id', '=', self.env.user.company_id.id)])
        purchase_ids = []
        for record in self:
            for raw_material in record.procurement_raw_material_ids:
                if not raw_material.partner_id:
                    raise ValidationError("Please select the vendor for product %s" % (
                        raw_material.product_id.name))
                purchase_order_vals = {}
                order_line_data = []
                purchase_id = self.env['purchase.order'].search(
                    [('project_id', '=', record.project_id.id),
                     ('partner_id', '=', raw_material.partner_id.id),
                     ('state', 'not in', ('purchase', 'done', 'cancel'))
                     ])
                purchase_ids.extend(purchase_id.ids)
                if not purchase_id:
                    purchase_order_vals.update({
                        'partner_id': raw_material.partner_id.id,
                        'date_order': fields.Datetime.now(),
                        'company_id': self.env.user.company_id.id,
                        'picking_type_id': picking_type_id.id,
                        'user_id': self.env.user.id or '',
                        'task_id': task_id.id,
                        #'project_name': record.project_id.project_name,
                    })
                    purchase_id = self.env['purchase.order'].create(
                        purchase_order_vals)
                    purchase_ids.append(purchase_id.id)
                if purchase_id and \
                        raw_material.partner_id.id == purchase_id.partner_id.id:
                    line_exist = purchase_id.order_line.filtered(lambda line: line.product_id.id == raw_material.product_id.id and
                                                                 line.price_unit == raw_material.cost)
                    if line_exist:
                        line_exist[0].write(
                            {'product_qty': line_exist[0].product_qty + raw_material.order_qty})
                    else:
                        order_line_data.append((0, 0, {
                            'product_id': raw_material.product_id.id,
                            'name': raw_material.product_id.display_name,
                            'date_planned': fields.Datetime.now(),
                            'company_id': self.env.user.company_id.id,
                            'product_qty': raw_material.order_qty,
                            'product_uom': raw_material.product_id.product_tmpl_id.uom_po_id.id,
                            #'dummy_price_unit': raw_material.cost,
                            'price_unit': raw_material.cost,
                            'account_analytic_id': record.project_id.analytic_account_id.id,
                        }))
                        purchase_id.order_line = order_line_data
            form = self.env.ref('purchase.purchase_order_form', False)
            tree = self.env.ref('purchase.purchase_order_tree', False)
            tree_id = tree.id if tree else False
            form_id = form.id if form else False
            action = self.env.ref('purchase.purchase_rfq')
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'view_mode': action.view_mode,
                'target': action.target,
                'context': action.context,
                'res_model': action.res_model,
            }
            result['domain'] = [('id', 'in', purchase_ids)]
            return result
