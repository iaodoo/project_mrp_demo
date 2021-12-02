# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, api
from collections import defaultdict
from odoo.tools.float_utils import float_compare, float_round, float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                          help="Fill this only if you want automatic analytic accounting entries on production orders.")

    part_number = fields.Char(string="Component Part Number")

    # def _action_assign(self):
    #     res = super(StockMove, self)._action_assign()
    #     assigned_moves = self.env['stock.move']
    #     partially_available_moves = self.env['stock.move']
    #     reserved_availability = {move: move.reserved_availability for move in self}
    #     roundings = {move: move.product_id.uom_id.rounding for move in self}
    #     move_line_vals_list = []
    #     for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
    #         rounding = roundings[move]
    #         missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
    #         missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
    #         if move.procure_method == 'make_to_order' or move.picking_id.backorder_id:
    #             need = missing_reserved_quantity
    #             if float_is_zero(need, precision_rounding=rounding):
    #                 assigned_moves |= move
    #                 continue
    #             # Reserve new quants and create move lines accordingly.
    #             existing_lot_number = self.env['stock.production.lot'].search([
    #                 ('name', '=', move.part_number)])
    #             available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id, lot_id=existing_lot_number)
    #             if available_quantity <= 0:
    #                 continue
    #             taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, lot_id=existing_lot_number, strict=False)
    #             if float_is_zero(taken_quantity, precision_rounding=rounding):
    #                 continue
    #             if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
    #                 assigned_moves |= move
    #             else:
    #                 partially_available_moves |= move
    #     self.mapped('picking_id')._check_entire_pack()
    #     partially_available_moves.write({'state': 'partially_available'})
    #     assigned_moves.write({'state': 'assigned'})
    #     return res

    def _get_new_picking_values(self):
        """
            Method Override to update branch_id in new picking vals.
        """
        data = super(StockMove, self)._get_new_picking_values() or {}
        data.update({
            'sale_type': self.sale_line_id.order_id and
            self.sale_line_id.order_id.sale_type or False,
            'project_size_id': self.sale_line_id.order_id.project_size_id and
            self.sale_line_id.order_id.project_size_id.id
        })
        return data

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        """ Create or update move lines.
        """
        if self.part_number and not lot_id:
            lot_id = self.env['stock.production.lot'].search([
                    ('name', '=', self.part_number)])
        if not lot_id:
            lot_id = self.env['stock.production.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        taken_quantity = min(available_quantity, need)

        # `taken_quantity` is in the quants unit of measure. There's a possibility that the move's
        # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
        # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
        # to convert `taken_quantity` to the move's unit of measure with a down rounding method and
        # then get it back in the quants unit of measure with an half-up rounding_method. This
        # way, we'll never reserve more than allowed. We do not apply this logic if
        # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
        # will take care of changing the UOM to the UOM of the product.
        if not strict:
            taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom, rounding_method='DOWN')
            taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id, rounding_method='HALF-UP')

        quants = []

        if self.product_id.tracking == 'serial':
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                taken_quantity = 0

        try:
            if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                quants = self.env['stock.quant']._update_reserved_quantity(
                    self.product_id, location_id, taken_quantity, lot_id=lot_id,
                    package_id=package_id, owner_id=owner_id, strict=strict
                )
        except UserError:
            taken_quantity = 0

        # Find a candidate move line to update or create a new one.
        for reserved_quant, quantity in quants:
            to_update = self.move_line_ids.filtered(lambda ml: ml._reservation_is_updatable(quantity, reserved_quant))
            if to_update:
                to_update[0].with_context(bypass_reservation_update=True).product_uom_qty += self.product_id.uom_id._compute_quantity(quantity, to_update[0].product_uom_id, rounding_method='HALF-UP')
            else:
                if self.product_id.tracking == 'serial':
                    for i in range(0, int(quantity)):
                        self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant))
                else:
                    self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
        return taken_quantity

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        result = super(StockMove, self) \
            ._prepare_move_line_vals(quantity, reserved_quant)
        ''' This method create auto generate lot/serial number
            when picking type is incoming, product track by lot/serial number
            and auto generate lot/serial number configation set true.
        '''

        if self.picking_type_id.code == 'incoming' and \
                self.product_id.tracking != 'none' and self.purchase_line_id.part_number:
            lot_id = False
            lot_vals = {
                'name': self.purchase_line_id.part_number,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom.id,
                'company_id': self.env.user.company_id.id
            }
            existing_lot_number = self.env['stock.production.lot'].search([
                ('name', '=', self.purchase_line_id.part_number)])
            if self.picking_type_id.use_existing_lots and existing_lot_number:
                lot_id = existing_lot_number
            if self.picking_type_id.use_create_lots and not lot_id:
                lot_id = self.env['stock.production.lot'] \
                    .sudo().create(lot_vals)
            if lot_id:
                result.update({'lot_id': lot_id.id,
                               'lot_name': lot_id.name})
        return result

    def _adjust_procure_method(self):
        """ This method will try to apply the procure method MTO on some moves if
        a compatible MTO route is found. Else the procure method will be set to MTS
        """
        # Prepare the MTSO variables. They are needed since MTSO moves are handled separately.
        # We need 2 dicts:
        # - needed quantity per location per product
        # - forecasted quantity per location per product
        mtso_products_by_locations = defaultdict(list)
        mtso_needed_qties_by_loc = defaultdict(dict)
        mtso_free_qties_by_loc = {}
        mtso_moves = self.env['stock.move']

        for move in self:
            product_id = move.product_id
            domain = [
                ('location_src_id', '=', move.location_id.id),
                ('location_id', '=', move.location_dest_id.id),
                ('action', '!=', 'push')
            ]
            rules = self.env['procurement.group']._search_rule(
                False, product_id, move.warehouse_id, domain)
            if rules:
                if rules.procure_method in ['make_to_order', 'make_to_stock']:
                    move.procure_method = rules.procure_method
                else:
                    # Get the needed quantity for the `mts_else_mto` moves.
                    mtso_needed_qties_by_loc[
                        rules.location_src_id].setdefault(product_id.id, 0)
                    mtso_needed_qties_by_loc[rules.location_src_id][
                        product_id.id] += move.product_qty

                    # This allow us to get the forecasted quantity in batch
                    # later on
                    mtso_products_by_locations[
                        rules.location_src_id].append(product_id.id)
                    mtso_moves |= move
            else:
                move.procure_method = 'make_to_stock'

        # Get the forecasted quantity for the `mts_else_mto` moves.
        for location, product_ids in mtso_products_by_locations.items():
            # products = self.env['product.product']
            for move in mtso_moves:
                if move.product_id.id in product_ids:
                    existing_lot_number = self.env['stock.production.lot'].search([
                        ('name', '=', move.part_number)])
                    if existing_lot_number:
                        product_browse = self.env['product.product'].browse(move.product_id.id).with_context(
                            location=location.id, lot_id=existing_lot_number.id)
                        if not mtso_free_qties_by_loc:
                            mtso_free_qties_by_loc[location] = {
                                move.product_id.id: product_browse.free_qty}
                        else:
                            mtso_free_qties_by_loc[location][
                                move.product_id.id] = product_browse.free_qty
                    else:
                        if not mtso_free_qties_by_loc:
                            mtso_free_qties_by_loc[location] = {
                                move.product_id.id: 0.0}
                        else:
                            mtso_free_qties_by_loc[location][
                                move.product_id.id] = 0.0
            # mtso_free_qties_by_loc[location] = {product.id: product.free_qty for product in products}

        # Now that we have the needed and forecasted quantity per location and per product, we can
        # choose whether the mtso_moves need to be MTO or MTS.
        for move in mtso_moves:
            needed_qty = move.product_qty
            forecasted_qty = mtso_free_qties_by_loc[
                move.location_id][move.product_id.id]
            if float_compare(needed_qty, forecasted_qty, precision_rounding=product_id.uom_id.rounding) <= 0:
                move.procure_method = 'make_to_stock'
                mtso_free_qties_by_loc[move.location_id][
                    move.product_id.id] -= needed_qty
            else:
                move.procure_method = 'make_to_order'


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    mail_date = fields.Date(
        string='Deadline Date (Ship/Mail Date)'
    )

# class StockRule(models.Model):
#     _inherit = 'stock.rule'

#     @api.model
#     def _run_manufacture(self, procurements):
#         if procurements:
#             stock_move = procurements[0][0].values['move_dest_ids']
#             existing_lot_number = self.env['stock.production.lot'].search([
#                 ('name', '=', stock_move.part_number)])
#             if existing_lot_number:
#                 product_browse = self.env['product.product'].browse(stock_move.product_id.id).with_context(lot_id=existing_lot_number.id)
#                 if product_browse.free_qty:
#                     stock_rule = procurements[0][1]
#                     new_quantity = procurements[0][0].product_qty - product_browse.free_qty
#                     new_procurement = procurements[0][0]._replace(product_qty=new_quantity)
#                     procurements = [(new_procurement,stock_rule)]
#         res = super(StockRule,self)._run_manufacture(procurements)