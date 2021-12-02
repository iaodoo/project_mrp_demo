# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Project Cost Management
    raw_material_line_ids = fields.One2many(
        'project.raw.material', 'sale_id', string='Raw Material Lines', copy=False)
    process_line_ids = fields.One2many(
        'project.process', 'sale_id', string='Process Cost Lines', copy=False)

    # Project Process
    sale_process_ids = fields.One2many(
        'sale.order.process', 'sale_id', string='Process', copy=True)

    state = fields.Selection(selection_add=[
        ('to approve', 'To Approve'),
    ], string='Status', readonly=True, copy=False, index=True,
        track_visibility='onchange', track_sequence=3, default='draft')

    # Sale Type
    sale_type = fields.Selection([
        ('direct', 'Direct'), ('supply', 'Supply'),
        ('supply_install', 'Supply & Install')
    ], help="Sale Type is used  for type of sale in SaleOrder", string="Project Scope", copy=False)
    project_size_id = fields.Many2one('project.size', string="Project Type",
                                      help="Project Type details in SaleOrder",
                                      copy=False)

    email_cc = fields.Char(string="Email CC")


    # sale_project_costing
    related_project_id = fields.Many2one(
        'project.project', compute='_get_related_project', string="Related Project")
    no_of_project = fields.Integer(
        compute='_get_related_project', string="Total Projects")

    # sale_crm_extension
    project_name = fields.Char(string="Project Name")

    # sale_approval
    date_approve = fields.Date('Approval Date', index=True,
                               copy=False, track_visibility='onchange')
    down_payment = fields.Float(string="Down Payment")
    simple_sale_order = fields.Boolean(string="Simple Sale Order",
                                       compute='_compute_simple_sale_order')

    @api.depends('order_line')
    def _compute_simple_sale_order(self):
        """
        Define compute function to show the confirm sale button or plan project
        button.
        :return:
        """
        for record in self:
            record.simple_sale_order = False
            if record.order_line:
                if all((line.product_id.type == 'service' and line.product_id.service_tracking == 'no') or \
                       (line.product_id.type != 'service' and not line.product_id.bom_ids) for line in record.order_line):
                    record.simple_sale_order = True
                else:
                    record.simple_sale_order = False
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        mail_post_autofollow = self._context.get('mail_post_autofollow')
        res =  super(SaleOrder, self.with_context(mail_post_autofollow=False)).message_post(**kwargs)
        if kwargs.get('partner_ids') and not mail_post_autofollow:
            partner_ids = set(kwargs.get('partner_ids') or [])
            self.message_unsubscribe(list(partner_ids))
        return res

    @api.onchange('sale_type')
    def onchange_sale_type(self):
        """
        Function define to change the project_size_id value based on sale_type.
        :return:
        """
        if not self.sale_type or self.sale_type == 'direct':
            self.project_size_id = False

    # Project Cost Management
    # def _get_actual_raw_material_cost(self):
    #     for rec in self:
    #         rec.actual_raw_material_cost = sum(
    #             rec.raw_material_line_ids.mapped('total_raw_material_cost'))

    @api.model
    def default_get(self, fields):
        res = super(SaleOrder, self).default_get(fields)
        project_size_id = self.env['project.size'].search([], limit=1)
        res.update({'sale_type': 'supply'})
        if project_size_id:
            res.update({'project_size_id': project_size_id.id})
        return res

    # Project Process
    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        for record in self:
            if record.related_project_id:
                record.order_line.write(
                    {'project_sale_id': record.related_project_id.id or ''})
                record.raw_material_line_ids.write(
                    {'project_id': record.related_project_id.id or ''})
                record.process_line_ids.write(
                    {'project_id': record.related_project_id.id or ''})
        return result

    # Project Process
    @api.onchange('project_size_id')
    def set_project_process(self):
        """
        This method through set Process details in Sale order.
        """
        Process = self.env['process.process']
        self.sale_process_ids = False
        sale_process_vals = {}
        if self.project_size_id:
            process_id = Process.search(
                [('project_size_id', '=', self.project_size_id.id)])
            for process in process_id:
                sale_process_vals.update({
                    'process_id': process.id,
                })
                self.sale_process_ids = [(0, 0, sale_process_vals)]

    # sale_approval
    def button_approve(self, force=False):
        """method to approve sale order"""
        if not self.env.user.has_group('project_process_manufacturing.group_plan_project'):
            raise ValidationError(
                "Only Plan Project manager can approve sale order.")
        self.write({'date_approve': fields.Date.
                    context_today(self)})
        if not self.raw_material_line_ids and any(line.product_id.bom_ids for line in self.order_line):
            raise ValidationError(
                "Component Product are not Set please reconfigure the Manufacture Product in Sale order Line.")
        if self.raw_material_line_ids and any(not line.part_number for line in self.raw_material_line_ids):
            raise ValidationError(
                "Please Set the Part Number for all Component Product.")
        sftp_configuration = self.env['sftp.configuration'].search([], limit=1)
        if sftp_configuration:
            file_name = self.name+'_'+self.partner_id.name.replace(' ','_') or ""
            if sftp_configuration.sftp_write:
                sftp_configuration.create_file_remote_server(file_name)
            else:
                file_path = sftp_configuration.root_folder or ""
                sftp_configuration.create_pdf_file(
                    file_path=file_path, file_name=file_name)
        self.action_confirm()


    def button_confirm_sale(self):
        """
        Define function to confirm sale order with default sale flow.
        :return:
        """
        return super(SaleOrder, self).action_confirm()

    @api.model
    def create(self, vals):
        ctx = dict(self._context)
        ctx.update({
            'created_from': 'sale',
        })
        return super(SaleOrder, self.with_context(ctx)).create(vals)

    def create_project(self, project_id):
        Project = self.env['project.project']
        project_stage_id = self.env['project.stage'].search(
            [('case_default', '=', True)])
        stage_id = self.env.ref(
            'project_process_manufacturing.project_stage_new').id
        domain = []
        if project_id and project_id.type_ids:
            domain.append(
                ('name', 'not in', project_id.type_ids.mapped('name')))
        domain.append((
            'id', 'in',
            (self.env.ref('project.project_stage_data_0').id,
             self.env.ref('project_process_manufacturing.project_stage_1').id,
             self.env.ref('project_process_manufacturing.project_stage_2').id,
             self.env.ref('project_process_manufacturing.project_stage_3').id,
             self.env.ref('project_process_manufacturing.project_stage_4').id,
             self.env.ref('project_process_manufacturing.project_stage_5').id,
             self.env.ref('project_process_manufacturing.project_stage_6').id
             )))
        project_task_stage_id = self.env['project.task.type'].search(domain)
        for order in self:
            if project_id:
                project_id.write({
                    'name': 'PRJ - ' + order.name,
                    'sale_type': order.sale_type,
                    'stage_id': project_stage_id.id or False,
                    'project_size_id': order.project_size_id and order.project_size_id.id,
                    'sale_project_id': order.id or False,
                    'partner_id': order.partner_id.id,
                    'job_number': order.name,
                    'privacy_visibility': 'followers',
                })
            else:
                project_id = Project.create(
                    {'name': 'PRJ - ' + order.name,
                     'sale_type': order.sale_type,
                     'project_title': order.project_title,
                     'stage_id': project_stage_id.id or False,
                     'project_size_id': order.project_size_id and order.project_size_id.id,
                     'sale_project_id': order.id or False,
                     'partner_id': order.partner_id.id,
                     'job_number': order.name,
                     'privacy_visibility': 'followers',
                     })
            project_task_stage_id.write(
                {'project_ids': [(4, project_id.id, None)]})
            order.order_line.write({'project_sale_id': project_id.id})
            order.raw_material_line_ids.write({'project_id': project_id.id})
            order.process_line_ids.write({'project_id': project_id.id})

            project_sale_id = self.env['project.project'].search([
                ('sale_project_id', '=', order.id),
                ('stage_id', '=', stage_id)
            ])
            process_ids = self.env['process.process'].search([
                ('project_size_id', '=', order.project_size_id.id)
            ])
            if project_sale_id and process_ids:
                for project_sale in project_sale_id:
                    new_process = []
                    if not project_sale.project_process_ids:
                        for process in process_ids:
                            new_process += [(0, 0, {
                                'process_id': process.id,
                                'user_id': process.user_id and process.user_id.id or False,
                            })]
                        project_sale.project_process_ids = new_process
        return project_id

    # sale_project_costing
    def _get_related_project(self):
        project_cancel_stage_id = self.env.ref(
            'project_process_manufacturing.project_stage_cancel')
        for rec in self:
            project_id = self.env['project.project'].search(
                [('sale_project_id', '=', rec.id), ('stage_id', '!=', project_cancel_stage_id.id)], limit=1)
            total_project = self.env['project.project'].search_count(
                [('sale_project_id', '=', rec.id)])
            rec.no_of_project = total_project
            if project_id:
                rec.related_project_id = project_id.id
            else:
                rec.related_project_id = False

    # sale_project_costing
    def action_view_project(self):
        project_id = self.env['project.project'].search(
            [('sale_project_id', '=', self.id)])
        action = self.env.ref(
            'project.open_view_project_all_config').read()[0]
        if len(project_id) > 1:
            action['domain'] = [('id', 'in', project_id.ids)]
        elif len(project_id) == 1:
            action['views'] = [
                (self.env.ref('project.edit_project').id, 'form')]
            action['res_id'] = project_id.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    # def _prepare_invoice(self):
    #     invoice_vals = super(SaleOrder, self)._prepare_invoice()
    #     invoice_vals.update({'sale_type': self.sale_type,
    #                          'project_size_id': self.project_size_id.id,
    #                          'project_name': self.project_name})
    #     return invoice_vals

    def _get_onchange_create(self):
        return OrderedDict([
            ('set_project_process', ['sale_process_ids']),
            ('set_raw_process_material', ['raw_material_line_ids']),
        ])

    # project_process_manufacturing
    def action_confirm(self):
        """it will check if sale order need approval or not and change\
        stage accordingly"""
        if not self.sale_type:
            raise ValidationError(
                "Please select project scope before confirmation of quotation.")
        if not self.order_line:
            raise ValidationError(
                "Please select Order Items before confirmation of quotation.")
        if self.state in ('draft', 'sent'):
            if self.company_id.so_double_validation == 'one_step'\
                or (self.company_id.so_double_validation == 'two_step'
                    and self.amount_total > self.env.user.company_id.
                    currency_id._convert(
                        self.company_id.so_double_validation_amount,
                        self.currency_id, self.company_id,
                        self.date_order or fields.Date.today())
                    ):
                if self.is_credit_check == True:
                    self.write({'state': 'to approve'})
                else:
                    self.write({'state': 'credit_check',
                                'is_check_email_send': True})
        elif self.state == 'to approve':
            is_follower = False
            if self.partner_id in self.message_follower_ids.mapped('partner_id'):
                is_follower = True
            result = super(SaleOrder, self).action_confirm()
            if not is_follower:
                self.message_unsubscribe([self.partner_id.id])

            for record in self:
                if not record.order_line:
                    raise ValidationError(_(
                        'Quotation should not be confirmed without quotation lines. %s.')
                        % self.name)
                if record.sale_type == 'direct' and record.sale_process_ids.\
                        filtered(lambda self: self.is_manufacturing):
                    record.create_sale_production_order()
                if record.sale_type and \
                        record.sale_type != 'direct':
                    project_id = self.env['project.project'].search([
                        ('sale_project_id', '=', record.id)])
                    project_id = record.create_project(project_id)
            return result

    # project_process_manufacturing
    def create_sale_production_order(self):
        ''' Create Manufacturing order when sale type is direct'''
        production_vals = {}
        picking_type_id = self.env['stock.picking.type'].\
            search([('code', '=', 'mrp_operation'),
                    ('warehouse_id.company_id', '=', self.env.user.company_id.id)])
        for line in self.order_line:
            bom_id = self.env['mrp.bom'].search(
                [('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)], limit=1)
            production_id = self.env['mrp.production'].search(
                [('sale_order_line_id', '=', line.id)])
            if bom_id and not production_id:
                production_vals.update({
                    'product_id': line.product_id.id,
                    'sale_type': self.sale_type or '',
                    'project_size_id': self.project_size_id and self.project_size_id.id,
                    'picking_type_id': picking_type_id and picking_type_id.id,
                    'company_id': self.env.user.company_id.id,
                    'sale_production_id': self.id or '',
                    'sale_order_line_id': line.id
                })
                mrp_production_id = self.env['mrp.production'].new(
                    production_vals)
                mrp_production_id.onchange_product_id()
                mrp_production_id._cache.update({
                    'product_qty': line.product_uom_qty
                })
                vals = self.env['mrp.production']._convert_to_write(
                    mrp_production_id._cache)
                mrp_production_id = self.env['mrp.production'].create(vals)

    def action_cancel(self):
        """ Method is override to Cancel Manufacturing order
        related to sale order.When sale type is direct.
        """
        result = super(SaleOrder, self).action_cancel()
        for record in self:
            project_id = self.env['project.project'].search([
                ('sale_project_id', '=', record.id),
                ('project_stage_visible', 'not in', ('done', 'cancel'))
            ])
            if project_id:
                raise ValidationError(_(
                    "This Order can't be Cancel. To Cancel this Order before to Cancel Related Project"
                ))
            if record.sale_type == 'direct':
                mrp_production_id = self.env[('mrp.production')].\
                    search([('sale_production_id', 'in', self.ids),
                            ('state', 'not in', ('done', 'cancel'))])
                if mrp_production_id:
                    mrp_production_id.action_cancel()
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # project_process_manufacturing
    mrp_remaining_qty = fields.Float(
        string='Remaining Qty', compute='_get_remaining_manufactured_qty')
    mrp_remaining_qty_add = fields.Float(string='Remaining Quantity')

    fg_part_no_description = fields.Text(string="Part No# Description")

    # Project Cost Management
    project_sale_id = fields.Many2one("project.project", string="Project")
    qty_available = fields.Float(
        "Available Quantity", compute='_compute_available_quantities')

    # Project Cost Management
    @api.onchange('product_id')
    def _compute_available_quantities(self):
        Quant = self.env['stock.quant']
        prod_obj = self.env['product.product']
        comp_id = self.env.user.company_id
        qty_available = 0.0
        for record in self:
            prod_id = prod_obj.search([('product_tmpl_id', '=',
                                        record.product_id.product_tmpl_id.id)],
                                      limit=1)
            if prod_id and comp_id:
                domain_quant = [
                    ('product_id', '=', prod_id.id),
                    ('company_id', '=', comp_id.id),
                ]
                quants_res = dict((item['product_id'][0],
                                   item['quantity'] - item[
                                       'reserved_quantity'])
                                  for item in Quant.read_group(domain_quant,
                                                               ['product_id',
                                                                'quantity',
                                                                'reserved_quantity'],
                                                               [
                                                                   'product_id'],
                                                               orderby='id')
                                  )
                qty_available = quants_res.get(prod_id.id, 0.0)
            record.qty_available = qty_available

    # project_process_manufacturing
    def _get_remaining_manufactured_qty(self):
        produced_qty = 0.0
        for rec in self:
            productions = \
                self.env['mrp.production'].search([
                    ('project_id', '=', rec.project_id.id),
                    ('state', '!=', 'cancel'),
                    ('product_id', '=', rec.product_id.id),
                    ('sale_order_line_id', '=', rec.id)])
            if productions:
                produced_qty = sum(productions.mapped('product_qty'))
            rec.mrp_remaining_qty = produced_qty

    @api.model
    def create(self, vals):
        res = super(SaleOrderLine, self).create(vals)
        row_material_obj = self.env['project.raw.material']
        process_obj = self.env['project.process']
        for line in res:
            if not line.product_id:
                return
            prepeare_raw_vals = {}
            prepare_process_vals = {}
            bom_id = line.product_id.bom_ids and line.product_id.bom_ids[
                0] or False
            if bom_id:
                exact_bom_line = self.env['mrp.bom.line']
                for current_line in bom_id.bom_line_ids:
                    if not current_line._skip_bom_line(line.product_id):
                        exact_bom_line += current_line
                if exact_bom_line:
                    bom_lines = self.env['mrp.bom.line']
                    not_routing_set_material = self.env['mrp.bom.line'].search([
                        ('task_routing_ids', '=', False),
                        ('id', 'in', exact_bom_line.ids)])
                    material_count = len(not_routing_set_material)
                    limit = material_count
                    if limit < bom_id.raw_material_count:
                        limit = bom_id.raw_material_count - material_count
                    routing_set_material = self.env['mrp.bom.line'].search([
                        ('task_routing_ids', '!=', False),
                        ('id', 'in', exact_bom_line.ids)], limit=limit)
                    if not_routing_set_material:
                        bom_lines += not_routing_set_material
                    if routing_set_material:
                        bom_lines += routing_set_material
                    if not bom_lines:
                        raise ValidationError(
                            "Raw  Material is not found for product %s as per default routing %s." %(
                                line.name,bom_id.routing_id.name))

                    for bom_line in bom_lines:
                        prepeare_raw_vals = {
                            'product_id': bom_line.product_id.id,
                            'order_qty': line.product_uom_qty or
                            bom_line.product_qty,
                            'finished_product_id': line.product_id.id or False,
                            'sale_order_line_id': res.id
                        }
                        raw_material_id = row_material_obj.create(
                            prepeare_raw_vals)
                        res.order_id.raw_material_line_ids = [
                            (4, raw_material_id.id)]
                        prepeare_raw_vals = {}
                    if bom_id.routing_id and \
                            bom_id.routing_id.operation_ids:
                        for process in bom_id.routing_id.operation_ids:
                            prepare_process_vals.update({
                                'process_id': process.id or '',
                                'product_uom_id': self.env.ref(
                                    'uom.product_uom_hour').id or '',
                                'quantity': process.time_cycle_manual or 0.0,
                                'product_id': line.product_id and line.product_id.id or False,
                                'routing_id': bom_id.routing_id.id or False,
                                'sale_order_line_id': res.id
                            })
                            process_line_id = process_obj.create(
                                prepare_process_vals)
                            res.order_id.process_line_ids = [
                                (4, process_line_id.id)]
                else:
                    raise ValidationError(
                        "Raw  Material is not Selected product %s." %(line.name))
        return res

    def write(self, vals):
        result = super(SaleOrderLine, self).write(vals)
        for record in self:
            if vals.get('product_uom_qty', False):
                raw_material_ids = self.order_id.raw_material_line_ids.filtered(
                    lambda x: x.sale_order_line_id.id == record.id)
                raw_material_ids.update(
                    {'order_qty': vals.get('product_uom_qty', False)})
        return result

    def unlink(self):
        for record in self:
            raw_material_ids = self.order_id.raw_material_line_ids.filtered(
                lambda x: x.sale_order_line_id.id == record.id)
            process_line_ids = self.order_id.process_line_ids.filtered(
                lambda x: x.sale_order_line_id.id == record.id)
            raw_material_ids.unlink()
            process_line_ids.unlink()
        return super(SaleOrderLine, self).unlink()
