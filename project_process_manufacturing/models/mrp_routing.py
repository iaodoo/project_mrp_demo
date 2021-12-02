# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, models


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Override to show only Process Related Routing."""
        if self._context.get('routing_id'):
            process_ids = self.search(
                [('routing_id', '=', self._context.get('routing_id'))])
            return process_ids.name_get()
        return super(MrpRoutingWorkcenter, self)._name_search(name, args, operator, limit, name_get_uid)
