# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class Task(models.Model):
    _inherit = "project.task"
    _description = "Task"

    is_procurement = fields.Boolean(
        "Show Procurement", compute='_check_procurement')
    is_manufacturing = fields.Boolean(
        "Show Manufacturing", compute='_check_procurement')
    is_service = fields.Boolean(
        "Show Service", compute='_check_procurement')
    product_id = fields.Many2one('product.product', compute='_check_procurement', string="Service Product",
        help="Service Product To link with Sale order")
    purchase_order_count = fields.Integer(
        compute='_count_purchase_order', string="Purchase Order")
    mrp_done_order_count = fields.Integer(
        compute='_count_mrp_order', string="Done Manufacturing Order")
    mrp_incomplete_order_count = fields.Integer(
        compute='_count_mrp_order', string="Inprogress Manufacturing Order")
    mrp_cancel_order_count = fields.Integer(
        compute='_count_mrp_order', string="Cancel Manufacturing Order")

    sale_type = fields.Selection([
        ('direct', 'Direct'), ('supply', 'Supply'),
        ('supply_install', 'Supply & Install')
    ], help="Sale Type is used  for type of sale in Task")
    project_size_id = fields.Many2one('project.size', string="Project Type",
                                      help="Project Type details in Task")
    task_visible = fields.Selection(related='stage_id.task_visible')
    process_id = fields.Many2one('process.process', string="Process")
    task_sequence = fields.Integer("Task Sequence")
    color = fields.Integer(string="Kanban Color", compute="set_kanban_color")
    hex_value = fields.Char(string="Hex Color value", compute="set_kanban_color")
    is_sub_task_processed = fields.Boolean(string="Is Sub-task Processed")


    def create_sale_order_line(self):
        """
        Define function to create the sale order line of service product which
        set in task.
        :return:
        """
        sale_order_id = self.project_id.sale_project_id
        order_line_vals = {
            'order_id': sale_order_id.id or False,
            'product_id':self.product_id.id,
            'product_template_id': self.product_id.product_tmpl_id.id or False,
            # 'product_uom_qty': 1,
            # 'product_uom': self.product_id.uom_id.id or False,
            # 'tax_id': self.product_id.taxes_id.ids or False,
            'name':self.product_id.name,
            'task_id': self.id,
        }
        sale_order_line = self.env['sale.order.line'].create(order_line_vals)
        sale_order_id.write({'order_line': [(4,sale_order_line.id)]})
        self.write({'sale_line_id': sale_order_line.id})

    def set_kanban_color(self):
        """
        Compute function define for change kanban color based on condition.
        :return:
        """
        for record in self:
            kanban_color = 0
            record.hex_value = ''
            if not record.user_id:
                if record.process_id and record.process_id.add_follower:
                    kanban_color = 4  # sky blue color #6CC1ED
                    record.hex_value = '#6CC1ED'
                elif record.parent_id:
                    record.hex_value = '#814968'
                    kanban_color = 5  # voilet color #814968
                else:
                    kanban_color = 6  # red color #EB7E7F
                    record.hex_value = '#EB7E7F'
            elif record.process_id and record.process_id.add_follower:
                kanban_color = 7  # Dark blue #2C8397
                record.hex_value = '#2C8397'
            elif record.parent_id:
                kanban_color = 10  # green color #30C381
                record.hex_value = '#30C381'
            record.color = kanban_color

    @api.constrains('stage_id')
    def check_stage_id(self):
        task_env = self.env['project.task']
        if self.stage_id:
            if self.stage_id.task_visible == 'new':
                self.set_to_draft()
            elif self.stage_id.task_visible == 'inprogress':
                self.action_inprogess()
            elif self.stage_id.task_visible == 'done':
                self.action_done()
            elif self.stage_id.task_visible == 'cancel':
                self.action_cancel()

    def action_inprogess(self):
        for task in self:
            if task.process_id.is_manufacturing:
                if not task.project_id.raw_material_line_ids:
                    raise ValidationError(_(
                        "This Project can't be confirm. Make sure you have added proper data in raw material line on project."
                    ))
                for rawmaterial in task.project_id.raw_material_line_ids:
                    if not rawmaterial.finished_product_id:
                        raise ValidationError(_(
                            "This task can't be confirm. Make sure you have added proper data in raw material line on project"
                        ))

            stage_id = self.env['project.task.type'].search([
                ('task_visible', '=', 'inprogress')], limit=1)
            if stage_id and stage_id != task.stage_id:
                task.stage_id = stage_id
        return True

    def set_to_draft(self):
        for task in self:
            stage_id = self.env['project.task.type'].search([
                ('task_visible', '=', 'new')], limit=1)
            if stage_id and stage_id != task.stage_id:
                task.stage_id = stage_id

    def _count_mrp_order(self):
        """
        Method to compute total number of MOs.
        """
        for rec in self:
            if rec.process_id and \
                    rec.process_id.is_manufacturing:
                order_ids = self.env['mrp.production'].search(
                    [('project_id', '=', rec.project_id.id)])
                mrp_done_count = 0
                mrp_incomplete_count = 0
                mrp_cancel_count = 0
                if order_ids:
                    for order in order_ids:
                        mrp_done_count += self.env['mrp.production'].search_count(
                            [('id', '=', order.id),
                             ('state', '=', 'done')])
                        mrp_incomplete_count += self.env[
                            'mrp.production'].search_count(
                            [('id', '=', order.id),
                             ('state', 'not in', ['done', 'cancel'])])
                        mrp_cancel_count += self.env[
                            'mrp.production'].search_count(
                            [('id', '=', order.id),
                             ('state', '=', 'cancel')])
                    rec.mrp_done_order_count = mrp_done_count or 0.0
                    rec.mrp_incomplete_order_count = mrp_incomplete_count or 0.0
                    rec.mrp_cancel_order_count = mrp_cancel_count or 0.0
                else:
                    rec.mrp_done_order_count = 0.0
                    rec.mrp_incomplete_order_count = 0.0
                    rec.mrp_cancel_order_count = 0.0
            else:
                rec.mrp_done_order_count = 0.0
                rec.mrp_incomplete_order_count = 0.0
                rec.mrp_cancel_order_count = 0.0

    def action_view_incomplete_mrp_order(self):
        """
        The function is used for return incomplete Manufacturing Order.
        :return:
        """
        order_ids = self.env['mrp.production'].search([
            ('project_id', '=', self.project_id.id)])
        all_orders = self.env['mrp.production']
        if order_ids:
            for order in order_ids:
                all_orders += self.env['mrp.production'].search([
                    '|', ('id', '=', order.id), ('origin', '=', order.name),
                    ('state', 'not in', ['done', 'cancel'])])
        action = self.env.ref('mrp.mrp_production_action').read()[0]
        if len(all_orders) > 1:
            action['domain'] = [('id', 'in', all_orders.ids)]
            action['context'] = {'search_default_manufacturing_order': 1}
        elif all_orders:
            form_view = [
                (self.env.ref('mrp.mrp_production_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [
                    (state, view) for state, view in action['views'] if
                    view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = all_orders.id
        return action

    def action_view_done_mrp_order(self):
        """
        Function is used to for return Done Manufacturing order.
        :return:
        """

        order_ids = self.env['mrp.production'].search(
            [('project_id', '=', self.project_id.id)])
        all_orders = self.env['mrp.production']
        if order_ids:
            for order in order_ids:
                all_orders += self.env['mrp.production'].search([
                    '|', ('id', '=', order.id), ('origin', '=', order.name),
                    ('state', '=', 'done')])
        action = self.env.ref('mrp.mrp_production_action').read()[0]
        if len(all_orders) > 1:
            action['domain'] = [('id', 'in', all_orders.ids)]
            action['context'] = {'search_default_manufacturing_order': 1}
        elif all_orders:
            form_view = [
                (self.env.ref('mrp.mrp_production_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [
                    (state, view) for state, view in action['views'] if
                    view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = all_orders.id
        return action

    def action_view_cancel_mrp_order(self):
        """
        Function is used to for return Cancel Manufacturing order.
        :return:
        """
        order_ids = self.env['mrp.production'].search(
            [('project_id', '=', self.project_id.id)])
        all_orders = self.env['mrp.production']
        if order_ids:
            for order in order_ids:
                all_orders += self.env['mrp.production'].search([
                    '|', ('id', '=', order.id), ('origin', '=', order.name),
                    ('state', '=', 'cancel')])
        action = self.env.ref('mrp.mrp_production_action').read()[0]
        if len(all_orders) > 1:
            action['domain'] = [('id', 'in', all_orders.ids)]
            action['context'] = {'search_default_manufacturing_order': 1}
        elif all_orders:
            form_view = [
                (self.env.ref('mrp.mrp_production_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [
                    (state, view) for state, view in action['views'] if
                    view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = all_orders.id
        return action

    def _count_purchase_order(self):
        """
         Method to compute total number of Purchase order.
        """
        for rec in self:
            if rec.process_id and \
                    rec.process_id.is_procurement:
                po_count = self.env['purchase.order'].search_count(
                    [('project_id', '=', rec.project_id.id)])
                rec.purchase_order_count = po_count
            else:
                rec.purchase_order_count = 0

    def action_view_purchase_order(self):
        """
            Method to Return Purchase Order.
        """
        order_ids = self.env['purchase.order'].search(
            [('project_id', '=', self.project_id.id)])
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        if len(order_ids) > 1:
            action['domain'] = [('id', 'in', order_ids.ids)]
        elif len(order_ids) == 1:
            action['views'] = [
                (self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = order_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.depends('stage_id')
    def _check_procurement(self):
        """
        This method through check procurement related task or not.
        """
        for task in self:
            task.is_service = False
            task.product_id = False
            if task.process_id and not task.process_id.is_manufacturing\
                    and not task.stage_id.id == self.env.ref('project_process_manufacturing.project_stage_1').id:
                task.is_manufacturing = False
            elif task.process_id and task.process_id.is_manufacturing:
                task.is_manufacturing = True
            else:
                task.is_manufacturing = False
            if task.process_id.is_service:
                task.is_service = True
                task.product_id = task.process_id.product_id.id
            if task.process_id and not task.process_id.is_procurement \
                    and not task.stage_id.id == self.env.ref('project_process_manufacturing.project_stage_1').id:
                task.is_procurement = False
            else:
                if task.process_id and task.process_id.is_procurement and \
                        task.stage_id.id == self.env.ref('project_process_manufacturing.project_stage_1').id:
                    task.is_procurement = True
                else:
                    task.is_procurement = False

    def action_open_create_production_wizard(self):
        view_id = self.env.ref(
            'project_process_manufacturing.view_production_order_request_form')
        return{
            'name': ('Create Production'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'create.production.wizard',
            'view_id': view_id.id,
            'target': 'new',
            'context': {'default_task_id': self.id}
        }

    def action_open_create_production_wizard_sub_task(self):
        view_id = self.env.ref(
            'project_process_manufacturing.view_production_order_request_form')
        return{
            'name': ('Create Sub Task'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'create.production.wizard',
            'view_id': view_id.id,
            'target': 'new',
            'context': {'default_task_id': self.id}
        }

    def create_production_order(self):
        """
            This method through generate Manufacturing order.
            When production set in task.
        """
        Production_id = False
        project_id = self.project_id
        MrpBom = self.env['mrp.bom']
        MrpProduction = self.env['mrp.production']
        MrpBomLine = self.env['mrp.bom.line']
        MrpRouting = self.env['mrp.routing']
        MrpRoutingWorkcenter = self.env['mrp.routing.workcenter']
        picking_type_id = self.env['stock.picking.type'].search(
            [('code', '=', 'mrp_operation'),
             ('warehouse_id.company_id', '=', self.env.user.company_id.id)])
        blank_raw_line = project_id.raw_material_line_ids.filtered(
            lambda line: not line.finished_product_id)
        if blank_raw_line:
            raise UserError(_('Finished Product no found in raw material.'))
        raw_line_sale_order_line_id = False
        if self._context.get('sale_order_line_for_mo'):
            raw_line_sale_order_line_id = self._context.get(
                'sale_order_line_for_mo')
        else:
            raw_line_sale_order_line_id = self.project_id.raw_material_line_ids.mapped(
                'sale_order_line_id')[0]
        if raw_line_sale_order_line_id:
            bom_id = False
            bom_id = MrpBom.search([
                ('product_tmpl_id', '=',
                    raw_line_sale_order_line_id.product_id.product_tmpl_id.id),
                ('active', '=', True)
            ], limit=1)
            production_vals = self.prepare_production_data(
                raw_line_sale_order_line_id, picking_type_id, project_id, bom_id)
            Production_id = MrpProduction.create(production_vals)

            # Code comment because routing sets from product start
            # if Production_id and Production_id.project_id.process_line_ids:
            #     routing_process_line = self.project_id.process_line_ids.filtered(
            #         lambda p: p.sale_order_line_id.id == raw_line_sale_order_line_id.id)
            #     if routing_process_line.mapped('routing_id'):
            #         Production_id.routing_id = routing_process_line.mapped('routing_id')[0].id
            # End Comment

            # Code comment because stage id already set from task.
            # if Production_id:
            #     if self.child_ids:
            #         if all(stage in ['done', 'cancel'] for stage in self.child_ids.mapped('task_visible')):
            #             new_stage_id = self.env['project.task.type'].search([
            #                 ('task_visible', '=', 'new')], limit=1)
            #             if new_stage_id:
            #                 self.child_ids.write({'stage_id': new_stage_id.id})
            #         inprogress_stage_id = self.env['project.task.type'].search([
            #             ('task_visible', '=', 'inprogress')], limit=1)
            #         if inprogress_stage_id:
            #             self.child_ids[0].write(
            #                 {'stage_id': inprogress_stage_id.id})
            # End comment
        return Production_id

    def prepare_bom_data(self, sale_order_line):
        """
            Prepare BoM dictionary.
        """
        if not sale_order_line:
            raise UserError("Related order item not found in sale order")
        res = {
            'product_tmpl_id': sale_order_line.product_id.product_tmpl_id.id,
            'product_qty': self._context.get('quantity').get(sale_order_line.id),
            'company_id': self.env.user.company_id.id,
            'product_uom_id': sale_order_line.product_uom.id,
        }
        return res

    def prepare_bom_line_data(self, raw_material, bom_id):
        """
            Prepare BoM for given finish product.
            Note: BoM line qty = qty in raw material line * order line product qty
            because in raw material line they enter raw material qty for only one finish product qty.
        """
        sale_order_line_id = raw_material.sale_order_line_id
        res = {
            'product_id': raw_material.product_id.id,
            'product_qty': raw_material.order_qty * sale_order_line_id.product_uom_qty,
            'bom_id': bom_id.id,
            'product_uom_id': raw_material.product_id.uom_id.id,
        }
        return res

    def prepare_production_data(self, sale_order_line, picking_type_id, project_id, bom_id):
        """
          This method through prepare  Mrp Production Order.
        """
        res = {
            'product_id': sale_order_line.product_id.id,
            'product_qty': self._context.get('quantity').get(sale_order_line.id),
            'company_id': self.env.user.company_id.id,
            'product_uom_id': sale_order_line.product_uom.id,
            'sale_order_line_id': sale_order_line.id,
            'sale_type': project_id.sale_type or '',
            'project_size_id': project_id.project_size_id and project_id.project_size_id.id,
            'picking_type_id': picking_type_id and picking_type_id.id,
            'task_id': self.id or '',
            'sale_production_id': project_id.sale_project_id.id or '',
            'project_title': project_id.project_title,
            'user_id': self.user_id.id,
        }
        mrp_production_id = self.env['mrp.production'].new(res)
        mrp_production_id.onchange_product_id()
        mrp_production_id._onchange_bom_id()
        mrp_production_id._compute_routing()
        mrp_production_id._cache.update({
            'product_qty': self._context.get('quantity').get(sale_order_line.id),
            'bom_id': bom_id.id,
        })
        mrp_production_id._onchange_move_raw()
        res = self.env['mrp.production']._convert_to_write(
            mrp_production_id._cache)
        return res

    def action_cancel(self):
        """
          This method through Cancel  Task.
        """
        for task in self:
            if task.is_procurement:
                purchase_id = self.env['purchase.order'].search(
                    [('project_id', '=', task.project_id.id),
                     ('state', 'not in', ('done', 'cancel'))
                     ])
                if purchase_id:
                    raise ValidationError(_(
                        "This Task can't be Cancel. To Cancel this task before to Cancel Related Purchase order"
                    ))
            if task.process_id.is_manufacturing:
                production_id = self.env['mrp.production'].search(
                    [('project_id', '=', task.project_id.id),
                     ('state', 'not in', ('done', 'cancel'))
                     ])
                if production_id:
                    raise ValidationError(_(
                        "This Task can't be Cancel. To Cancel this task before to Cancel Related Manufacturing order"
                    ))
            stage_id = self.env['project.task.type'].search([
                ('task_visible', '=', 'cancel')], limit=1)
            if stage_id and stage_id != task.stage_id:
                task.stage_id = stage_id

    def action_done(self):
        for task in self:
            purchase_id = self.env['purchase.order'].search(
                [('project_id', '=', task.project_id.id),
                 ('state', 'not in', ('done', 'cancel'))
                 ])
            production_id = self.env['mrp.production'].search(
                [('project_id', '=', task.project_id.id),
                 ('state', 'not in', ('done', 'cancel'))
                 ])
            if task.is_procurement and purchase_id:
                raise ValidationError(_(
                    "This Task can't be Done. To Done this task before to Done Related Purchase order"
                ))
            if task.process_id.is_manufacturing and production_id:
                raise ValidationError(_(
                    "This Task can't be Done. To Done this task before to Done Related Manufacturing order"
                ))
            stage_id = self.env['project.task.type'].search([
                ('task_visible', '=', 'done')], limit=1)
            if stage_id and stage_id != task.stage_id:
                task.stage_id = stage_id
        return

    def write(self, vals):
        """
         This method through check Project Task.
        """
        for rec in self:
            if rec.project_id.project_process_ids:
                rec.check_project_task()
        return super(Task, self).write(vals)

    def check_project_task(self):
        return True
        """Note: as of now bypass method by return, so multiple task can be in process"""
        """
        This method through check Previous task done
        after another task process.
        """
        for task in self:
            previous_task = task.search(
                [('project_id', '=', task.project_id.id),
                 ('task_sequence', '<', task.task_sequence),
                    ('stage_id', 'not in',
                     (self.env.ref('project_process_manufacturing.project_stage_2').id,
                      self.env.ref(
                          'project_process_manufacturing.project_stage_3').id
                      )
                     )
                 ])
            if previous_task:
                raise ValidationError(_(
                    'This cannot be set  \
                     to InProgress as previous task " %s"  is not done yet.')
                    % previous_task[0].name)
