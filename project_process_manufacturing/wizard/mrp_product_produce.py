# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, _
from odoo.tools.float_utils import float_round, float_compare
from odoo.exceptions import UserError
from datetime import datetime


class MrpProductProduce(models.TransientModel):
    _inherit = "mrp.product.produce"

    def do_produce(self):
        # Nothing to do for lots since values are created using default data (stock.move.lots)
        quantity = self.qty_producing
        if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(
                _("The production order for '%s' has no quantity specified.") % self.product_id.display_name)
        for move in self.production_id.move_finished_ids:
            if move.product_id.tracking == 'none' and move.state not in ('done', 'cancel'):
                rounding = move.product_uom.rounding
                if move.product_id.id == self.production_id.product_id.id:
                    move.quantity_done += float_round(
                        quantity, precision_rounding=rounding)
                elif move.unit_factor:
                    # byproducts handling
                    move.quantity_done += float_round(
                        quantity * move.unit_factor, precision_rounding=rounding)
        #self.check_finished_move_lots()
        if self.production_id.state == 'confirmed':
            self.production_id.write({
                'state': 'progress',
                'date_start': datetime.now(),
            })
        return {'type': 'ir.actions.act_window_close'}
