# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'
    _description = 'Change Production Qty'

    def change_prod_qty(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for wizard in self:
            production = wizard.mo_id
            produced = sum(production.move_finished_ids.filtered(
                lambda m: m.product_id == production.product_id).mapped('quantity_done'))
            if wizard.product_qty < produced:
                format_qty = '%.{precision}f'.format(precision=precision)
                raise UserError(_("You have already processed %s. Please input a quantity higher than %s ") % (
                    format_qty % produced, format_qty % produced))
            old_production_qty = production.product_qty
            production.write({'product_qty': wizard.product_qty})
            done_moves = production.move_finished_ids.filtered(
                lambda x: x.state == 'done' and x.product_id == production.product_id)
            qty_produced = production.product_id.uom_id._compute_quantity(
                sum(done_moves.mapped('product_qty')), production.product_uom_id)
            factor = production.product_uom_id._compute_quantity(
                production.product_qty - qty_produced, production.bom_id.product_uom_id) / production.bom_id.product_qty
            documents = {}
            final_lines = []
            boms, lines = production.bom_id.explode(
                production.product_id, factor, picking_type=production.bom_id.picking_type_id)
            if production.project_id:
                for raw_material in production.project_id.raw_material_line_ids:
                    old_lines = lines
                    if raw_material.finished_product_id.id == production.product_id.id:
                        for old_line in old_lines:
                            if old_line[0].product_id.id == raw_material.product_id.id:
                                final_lines.append(old_line)
                for line, line_data in final_lines:
                    move = production.move_raw_ids.filtered(
                        lambda x: x.bom_line_id.id == line.id and x.state not in ('done', 'cancel'))
                    if move:
                        move = move[0]
                        old_qty = move.product_uom_qty
                    else:
                        old_qty = 0
                    iterate_key = production._get_document_iterate_key(move)
                    if iterate_key:
                        document = self.env['stock.picking']._log_activity_get_documents(
                            {move: (line_data['qty'], old_qty)}, iterate_key, 'UP')
                        for key, value in document.items():
                            if documents.get(key):
                                documents[key] += [value]
                            else:
                                documents[key] = [value]

                    production._update_raw_move(line, line_data)

                production._log_manufacture_exception(documents)
                operation_bom_qty = {}
                for bom, bom_data in boms:
                    for operation in bom.routing_id.operation_ids:
                        operation_bom_qty[operation.id] = bom_data['qty']
                finished_moves_modification = self._update_finished_moves(
                    production, production.product_qty - qty_produced, old_production_qty)
                production._log_downside_manufactured_quantity(
                    finished_moves_modification)
                moves = production.move_raw_ids.filtered(
                    lambda x: x.state not in ('done', 'cancel'))
                moves._action_assign()
                for wo in production.workorder_ids:
                    operation = wo.operation_id
                    if operation_bom_qty.get(operation.id):
                        cycle_number = float_round(
                            operation_bom_qty[operation.id] / operation.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
                        wo.duration_expected = (operation.workcenter_id.time_start +
                                                operation.workcenter_id.time_stop +
                                                cycle_number * operation.time_cycle * 100.0 / operation.workcenter_id.time_efficiency)
                    quantity = wo.qty_production - wo.qty_produced
                    if production.product_id.tracking == 'serial':
                        quantity = 1.0 if not float_is_zero(
                            quantity, precision_digits=precision) else 0.0
                    else:
                        quantity = quantity if (quantity > 0) else 0
                    if float_is_zero(quantity, precision_digits=precision):
                        wo.finished_lot_id = False
                        wo._workorder_line_ids().unlink()
                    wo.qty_producing = quantity
                    if wo.qty_produced < wo.qty_production and wo.state == 'done':
                        wo.state = 'progress'
                    if wo.qty_produced == wo.qty_production and wo.state == 'progress':
                        wo.state = 'done'
                    # assign moves; last operation receive all unassigned moves
                    # TODO: following could be put in a function as it is similar as code in _workorders_create
                    # TODO: only needed when creating new moves
                    moves_raw = production.move_raw_ids.filtered(
                        lambda move: move.operation_id == operation and move.state not in ('done', 'cancel'))
                    if wo == production.workorder_ids[-1]:
                        moves_raw |= production.move_raw_ids.filtered(
                            lambda move: not move.operation_id)
                    moves_finished = production.move_finished_ids.filtered(
                        lambda move: move.operation_id == operation)  # TODO: code does nothing, unless maybe by_products?
                    moves_raw.mapped('move_line_ids').write(
                        {'workorder_id': wo.id})
                    (moves_finished + moves_raw).write({'workorder_id': wo.id})
                    if wo.state not in ('done', 'cancel'):
                        line_values = wo._update_workorder_lines()
                        wo._workorder_line_ids().create(line_values['to_create'])
                        if line_values['to_delete']:
                            line_values['to_delete'].unlink()
                        for line, vals in line_values['to_update'].items():
                            line.write(vals)

            else:
                return super(ChangeProductionQty, self).change_prod_qty()
        return {}
