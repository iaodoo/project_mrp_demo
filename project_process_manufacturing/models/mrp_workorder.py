# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    _description = 'Work Order'

    sale_type = fields.Selection([
        ('direct', 'Direct'), ('supply', 'Supply'),
        ('supply_install', 'Supply & Install')
    ], help="Sale Type is used  for type of sale in Work Order")
    project_size_id = fields.Many2one('project.size', string="Project Type",
                                      help="Project Type  details in  Work Order")

    part_number = fields.Char(string="Component Part Number")

    def open_tablet_view(self):
        if self.product_id.tracking != 'none' and not self.finished_lot_id:
            tracking_number = False
            if self.part_number:
                tracking_number = self.part_number
            elif self.production_id.batch_number:
                tracking_number = self.production_id.batch_number
            if tracking_number:
                lot_vals = {
                        'name': tracking_number,
                        'product_id': self.product_id.id,
                        'company_id': self.env.user.company_id.id
                }
                existing_lot_number = self.env['stock.production.lot'].search([
                    ('name','=',tracking_number)])
                if existing_lot_number:
                    self.finished_lot_id = existing_lot_number.id
                else:
                    self.finished_lot_id = self.env['stock.production.lot'] \
                           .sudo().create(lot_vals).id
            for raw in self.raw_workorder_line_ids:
                if raw.product_id.tracking != 'none' and not raw.lot_id:
                    for mo_raw in self.production_id.move_raw_ids:
                        if raw.product_id == mo_raw.product_id and mo_raw.part_number:
                            existing_lot_number = self.env['stock.production.lot'].search([
                                ('name','=',mo_raw.part_number)])
                            if existing_lot_number:
                                self.write({'raw_workorder_line_ids': [(1,raw.id,{'lot_id': existing_lot_number.id})]})
                                if raw.lot_id:
                                    for check in raw.check_ids:
                                        if not check.lot_id:
                                            check.write({'lot_id':raw.lot_id.id})
        return super(MrpWorkorder, self).open_tablet_view()

    @api.model
    def create(self, values):
        """
        This method override to set operation type in
        Work Order.
        """
        result = super(MrpWorkorder, self).create(values)
        for record in result:
            if record.production_id:
                record.sale_type = record.production_id.sale_type
                record.project_size_id = record.production_id.project_size_id
                if record.production_id.part_number:
                    record.part_number = record.production_id.part_number

        return result

    def record_production(self):
        result = super(MrpWorkorder, self).record_production()
        for record in self:
            project_process_id = self.env['project.process'].search([
                ('project_id', '=', record.production_id.project_id.id),
                ('process_id', '=', record.operation_id.id)
            ])
            for process in project_process_id:
                process_duration = process.used_process + \
                    sum(record.time_ids.mapped('duration'))
                process.write({'used_process': process_duration})
        return result
