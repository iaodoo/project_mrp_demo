# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _description = "Production"

    sale_type = fields.Selection([
        ('direct', 'Direct'), ('supply', 'Supply'),
        ('supply_install', 'Supply & Install')
    ], help="Sale Type is used  for type of sale in Manufacturing Orders")
    project_size_id = fields.Many2one('project.size', string="Project Type",
                                      help="Project Type details in Manufacturing Orders")
    task_id = fields.Many2one(
        'project.task', string="Task Details", copy=False)
    project_id = fields.Many2one("project.project",
                                 related='task_id.project_id',
                                 string="Project", copy=False, store=True)
    sale_production_id = fields.Many2one(
        'sale.order', string='Sale Order', copy=False)
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string="Sale order line", copy=False)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], string='Priority', index=True, default='1')
    # todo:related = 'product_id.sample_ok',
    partner_id = fields.Many2one(
        'res.partner', string='Customer', related='project_id.partner_id', store=True)

    produced_qty = fields.Float(
        compute='_get_produced_quantity', string="Produced Qty")
    project_name = fields.Char(
        related="project_id.project_name", string='Project Name', store=True)

    project_title = fields.Char(string='Project Title')

    project_group_by_mo = fields.Char(string="Project MO", store=True)

    part_number = fields.Char(string="Component Part Number")
    product_description = fields.Text(related="sale_order_line_id.name",
                                      string="Product Description")
    part_no_description = fields.Text(
        related="sale_order_line_id.fg_part_no_description",
        string="Product Part No# Description")


    # Custom Date Field Mail Date
    mail_date = fields.Date(
        string='Mail Date'
    )

    production_material_line_ids = fields.One2many(
        'mrp.production.material.line', 'production_id',
        string="Production Material Lines")

    def _get_produced_quantity(self):
        for rec in self:
            rec.produced_qty = sum(
                rec.finished_move_line_ids.mapped('qty_done'))

    def action_assign(self):
        """
        This method to override assign used Quantity
        in Rawmaterial.
        """
        result = super(MrpProduction, self).action_assign()
        for production in self:
            for consumed in production.move_raw_ids:
                project_raw_material_id = self.env['project.raw.material'].search(
                    [('project_id', '=', production.project_id.id)])
                if project_raw_material_id:
                    for rawmaterial in project_raw_material_id:
                        if consumed.product_id.id == rawmaterial.product_id.id:
                            rawmaterial.used_qty = consumed.reserved_availability or consumed.quantity_done
        return result

    def write(self, vals):
        """
        This method to override set used Quantity
        in Rawmaterial.
        """
        result = super(MrpProduction, self).write(vals)
        for production in self:
            for consumed in production.move_raw_ids:
                project_raw_material_id = self.env['project.raw.material'].search(
                    [('project_id', '=', production.project_id.id)])
                if project_raw_material_id:
                    for rawmaterial in project_raw_material_id:
                        if consumed.product_id.id == rawmaterial.product_id.id and (consumed.reserved_availability > 0 or consumed.quantity_done > 0):
                            rawmaterial.used_qty = consumed.reserved_availability or consumed.quantity_done
                            consumed.analytic_account_id = production.project_id.analytic_account_id.id
        return result

    def _generate_workorders(self, exploded_boms):
        workorders = self.env['mrp.workorder']
        original_one = False
        if self.project_id:
            for bom, bom_data in exploded_boms:
                temp_workorders = self._workorders_create(bom, bom_data)
                workorders += temp_workorders
                if temp_workorders:  # In order to avoid two "ending work orders"
                    if original_one:
                        temp_workorders[-1].next_work_order_id = original_one
                    original_one = temp_workorders[0]
        else:
            return super(MrpProduction, self)._generate_workorders(exploded_boms)
        return workorders

    # def _workorders_create(self, bom, bom_data):
    #     """
    #     :param bom: in case of recursive boms: we could create work orders for BoMs.
    #     """
    #     workorders = self.env['mrp.workorder']
    #     bom_qty = bom_data['qty']

    #     # Initial qty producing
    #     if self.product_id.tracking == 'serial':
    #         quantity = 1.0
    #     else:
    #         quantity = self.product_qty - \
    #             sum(self.move_finished_ids.mapped('quantity_done'))
    #         quantity = quantity if (quantity > 0) else 0
    #     if self.project_id and self.project_id.process_line_ids:
    #         for operation in self.project_id.process_line_ids.filtered(lambda p: p.product_id.id == self.product_id.id):
    #             operation.process_id.workcenter_id.costs_hour_account_id = self.project_id.analytic_account_id.id or 0.0
    #             cycle_number = float_round(
    #                 bom_qty / operation.process_id.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
    #             duration_expected = (operation.process_id.workcenter_id.time_start +
    #                                  operation.process_id.workcenter_id.time_stop +
    #                                  cycle_number * operation.process_id.time_cycle * 100.0 / operation.process_id.workcenter_id.time_efficiency)

    #             workorder = workorders.create({
    #                 'name': operation.process_id.name,
    #                 'production_id': self.id,
    #                 'workcenter_id': operation.process_id.workcenter_id.id,
    #                 'operation_id': operation.process_id.id,
    #                 'duration_expected': duration_expected,
    #                 'state': len(workorders) == 0 and 'ready' or 'pending',
    #                 'qty_producing': quantity,
    #                 'capacity': operation.process_id.workcenter_id.capacity,
    #                 'product_uom_id': self.product_id.uom_id.id,
    #                 'consumption': self.bom_id.consumption,
    #             })
    #             if workorders:
    #                 workorders[-1].next_work_order_id = workorder.id
    #                 workorders[-1]._start_nextworkorder()
    #             workorders += workorder

    #             moves_raw = self.move_raw_ids.filtered(
    #                 lambda move: move.operation_id == operation and move.bom_line_id.bom_id.routing_id == bom.routing_id)
    #             moves_finished = self.move_finished_ids.filtered(
    #                 lambda move: move.operation_id == operation)
    #             if len(workorders) == len(bom.routing_id.operation_ids):
    #                 moves_raw |= self.move_raw_ids.filtered(
    #                     lambda move: not move.operation_id and move.bom_line_id.bom_id.routing_id == bom.routing_id)
    #                 moves_raw |= self.move_raw_ids.filtered(
    #                     lambda move: not move.workorder_id and not move.bom_line_id.bom_id.routing_id)

    #                 moves_finished |= self.move_finished_ids.filtered(
    #                     lambda move: move.product_id != self.product_id and not move.operation_id)

    #             moves_raw.mapped('move_line_ids').write(
    #                 {'workorder_id': workorder.id})
    #             (moves_finished | moves_raw).write(
    #                 {'workorder_id': workorder.id})

    #             workorder._generate_wo_lines()
    #     else:
    #         return super(MrpProduction, self)._workorders_create(bom, bom_data)
    #     return workorders

    def _workorders_create(self, bom, bom_data):
        workorders = self.env['mrp.workorder']

        # Initial qty producing
        quantity = max(self.product_qty - sum(self.move_finished_ids.filtered(
            lambda move: move.product_id == self.product_id).mapped('quantity_done')), 0)
        quantity = self.product_id.uom_id._compute_quantity(
            quantity, self.product_uom_id)
        if self.product_id.tracking == 'serial':
            quantity = 1.0
        if self.product_id.routing_id:
            for operation in self.product_id.routing_id.operation_ids:
                workorder = workorders.create({
                    'name': operation.name,
                    'production_id': self.id,
                    'workcenter_id': operation.workcenter_id.id,
                    'product_uom_id': self.product_id.uom_id.id,
                    'operation_id': operation.id,
                    'state': len(workorders) == 0 and 'ready' or 'pending',
                    'qty_producing': quantity,
                    'consumption': self.bom_id.consumption,
                })
                if workorders:
                    workorders[-1].next_work_order_id = workorder.id
                    workorders[-1]._start_nextworkorder()
                workorders += workorder

                moves_raw = self.move_raw_ids.filtered(
                    lambda move: move.operation_id == operation)
                moves_finished = self.move_finished_ids.filtered(
                    lambda move: move.operation_id == operation)

                # - Raw moves from a BoM where a routing was set but no operation was precised should
                #   be consumed at the last workorder of the linked routing.
                # - Raw moves from a BoM where no rounting was set should be consumed at the last
                #   workorder of the main routing.
                if len(workorders) == len(bom.routing_id.operation_ids):
                    moves_raw |= self.move_raw_ids.filtered(
                        lambda move: not move.operation_id)
                    moves_raw |= self.move_raw_ids.filtered(
                        lambda move: not move.workorder_id)
                    moves_finished |= self.move_finished_ids.filtered(
                        lambda move: move.product_id != self.product_id and not move.operation_id)

                moves_raw.mapped('move_line_ids').write(
                    {'workorder_id': workorder.id})
                (moves_finished | moves_raw).write(
                    {'workorder_id': workorder.id})

                workorder._generate_wo_lines()
        else:
            return super(MrpProduction, self)._workorders_create(bom, bom_data)
        return workorders

    @api.depends('bom_id.routing_id', 'bom_id.routing_id.operation_ids')
    def _compute_routing(self):
        for production in self:
            if production.product_id and production.product_id.routing_id:
                production.routing_id = production.product_id.routing_id.id
            elif production.bom_id.routing_id.operation_ids:
                production.routing_id = production.bom_id.routing_id.id
            else:
                if not production.project_id:
                    production.routing_id = False
                else:
                    if production.project_id.process_line_ids:
                        routing_id = self.project_id.process_line_ids.filtered(
                            lambda p: p.product_id.id == production.product_id.id)
                        if routing_id:
                            production.routing_id = routing_id[0].routing_id

    def _prepare_wc_analytic_line(self, wc_line):
        if self.project_id and self.project_id.process_line_ids:
            wc = wc_line.workcenter_id
            project_process_id = self.env['project.process'].search(
                [('product_id', '=', wc_line.product_id.id),
                 ('project_id', '=', self.project_id.id),
                 ])
            for process in project_process_id:
                hours = process.used_process
                value = hours * process.cost
                account = wc.costs_hour_account_id.id
                return {
                    'name': wc_line.name + ' (H)',
                    'amount': -value,
                    'account_id': account,
                    'ref': wc.code,
                    'unit_amount': hours,
                    'type': 'process',
                }
        else:
            return super(MrpProduction, self)._prepare_wc_analytic_line(wc_line)

    def action_confirm(self):
        self._check_company()
        for production in self:
            if not production.move_raw_ids:
                raise UserError(_("In '%s' Bill Of Material '%s' Raw Material is not available.") % (production.bom_id.product_tmpl_id.name,production.product_id.display_name))
            if production.project_id:
                production.project_group_by_mo = production.name
            if production.origin:
                production.project_group_by_mo = production.origin
            for move_raw in production.move_raw_ids:
                move_raw.write({
                    'group_id': production.procurement_group_id.id,
                    'unit_factor': move_raw.product_uom_qty / production.product_qty,
                    'reference': production.name,  # set reference when MO name is different than 'New'
                })
            production._generate_finished_moves()
            production.move_raw_ids._adjust_procure_method()
            (production.move_raw_ids | production.move_finished_ids)._action_confirm()
        return True

    def unlink(self):
        """
        Override function to pass the context when call the action_cancel
        function.
        :return:
        """
        ctx = dict(self._context) or {}
        ctx.update({'cancel_from_unlink': True})
        return super(MrpProduction, self.with_context(ctx)).unlink()

    def action_cancel(self):
        """
        Inherit function to calculate the finished product qty to update in
        sale order line.
        :return:
        """
        res = super(MrpProduction, self).action_cancel()
        if self._context.get('cancel_from_unlink', False):
            return res
        else:
            for rec in self:
                remaining_qty = rec.product_qty
                qty_done = 0
                if rec.finished_move_line_ids:
                    qty_done = sum(rec.finished_move_line_ids.filtered(
                        lambda l: l.state == 'done').mapped('qty_done'))
                remaining_qty = remaining_qty - qty_done
                if rec.sale_order_line_id:
                    rec.sale_order_line_id.mrp_remaining_qty_add = \
                        rec.sale_order_line_id.mrp_remaining_qty_add - remaining_qty
            return res

    def _get_moves_raw_values(self):
        moves = []
        for production in self:
            factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id) / production.bom_id.product_qty
            boms, lines = production.bom_id.explode(production.product_id, factor, picking_type=production.bom_id.picking_type_id)
            count = 0
            for bom_line, line_data in lines:
                if bom_line.task_routing_ids and production.origin:
                    main_production = self.search([('name', '=', production.origin)])
                    if production.routing_id in bom_line.task_routing_ids:
                        if main_production.production_material_line_ids:
                            raw_material_ids = main_production.production_material_line_ids.filtered(
                                lambda l: l.routing_id in bom_line.task_routing_ids)
                            if raw_material_ids and bom_line.product_id in raw_material_ids.mapped('material_product_id'):
                                if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or\
                                        bom_line.product_id.type not in ['product', 'consu']:
                                    continue
                                moves.append(production._get_move_raw_values(bom_line, line_data))
                        else:
                            if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or \
                                    bom_line.product_id.type not in ['product', 'consu']:
                                continue
                            moves.append(production._get_move_raw_values(bom_line, line_data))
                else:
                    if bom_line.task_routing_ids:
                        if self.routing_id not in bom_line.task_routing_ids:
                            continue
                        count += 1
                        if production.bom_id.raw_material_count < count:
                            break
                        moves.append(production._get_move_raw_values(bom_line, line_data))
                    else:
                        if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or\
                                bom_line.product_id.type not in ['product', 'consu']:
                            continue
                        moves.append(production._get_move_raw_values(bom_line, line_data))
        return moves


class MrpProductionMaterialLine(models.Model):
    _name = "mrp.production.material.line"
    _description = "Production Material Line"
    _rec_name = "material_product_id"

    production_id = fields.Many2one('mrp.production', string="Production")
    routing_id = fields.Many2one('mrp.routing', string="Routing")
    component_product_id = fields.Many2one('product.product',
                                           string="Component Product")
    material_product_id = fields.Many2one('product.product',
                                 string="Raw Material Product")
