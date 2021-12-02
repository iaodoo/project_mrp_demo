# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, api, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    task_visible = fields.Selection([
        ('new', 'New'),
        ('inprogress', 'Inprogress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('to_approve', 'ToApprove'),
        ('approved', 'Approved'),
        ('waiting_customer_feedback', 'Waiting Customer Feedback')
    ], string="Task Tracker",
    )


class Project(models.Model):
    _inherit = 'project.project'

    sale_type = fields.Selection([
        ('direct', 'Direct'), ('supply', 'Supply'),
        ('supply_install', 'Supply & Install')
    ], help="Project Scope is used  for type of sale in Project",
        string="Project Scope")
    project_size_id = fields.Many2one('project.size', string="Project Type",
                                      help="Project Type details in Project")
    sale_project_id = fields.Many2one('sale.order', copy=False)
    project_name = fields.Char(
        related="sale_project_id.project_name", string="Project Name")
    finished_sale_line_ids = fields.One2many(
        'sale.order.line', 'project_sale_id', string='Ordered Items', copy=False)
    raw_material_line_ids = fields.One2many(
        'project.raw.material', 'project_id', string='Raw Material Lines')

    stage_id = fields.Many2one(
        'project.stage',
        'Stage',
        track_visibility='onchange',
        copy=False)
    kanban_state = fields.Selection(
        [('normal', 'In Progress'), ('blocked', 'Blocked'),
         ('done', 'Ready for next stage')],
        'Kanban State',
        track_visibility='onchange',
        help="A task's kanban state indicates special situations affecting it:\n"
        " * Normal is the default situation\n"
        " * Blocked indicates something is preventing the progress of this task\n"
        " * Ready for next stage indicates the task is ready to be pulled to the next stage",
        required=False,
        copy=False)
    project_stage_visible = fields.Selection([
        ('new', 'New'),
        ('inprogress', 'Inprogress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string="Project Stage Visible", default='new'
    )
    project_stage_name = fields.Char(
        compute='_get_stage_name', string="Project Stage Name")
    toc_done = fields.Boolean(string="TOC Done")
    coc_done = fields.Boolean(string="COC Done")
    project_process_ids = fields.One2many(
        'project.process.process', 'project_id',
        string='Project Process', copy=False)
    actual_done_date = fields.Date(string="Actual Completion Date")
    next_toc_coc_date = fields.Date(string='Next Toc Coc Date')
    process_line_ids = fields.One2many(
        'project.process', 'project_id', string='Process Cost Lines')
    job_number = fields.Char(string="Job Number")
    date_confirm = fields.Date(string="Confirmation Date")
    portal_task_count = fields.Integer(string='Portal Tasks',
                                       compute='_compute_portal_tasks')

    @api.depends('message_partner_ids')
    def _compute_portal_tasks(self):
        """
        Define the compute function _compute_portal_tasks to count portal
        tasks.
        :return:
        """
        project_task = self.task_ids.search([('project_id', '=', self.id)])
        portal_tasks = project_task.filtered(
            lambda task: task.partner_id in task.message_partner_ids)
        # import pdb; pdb.set_trace()
        self.portal_task_count = len(portal_tasks)

    def action_view_portal_tasks(self):
        """
        Define fuction action_view_portal_tasks to shows the portal tasks.
        :return:
        """
        list_view_id = self.env.ref('project.view_task_tree2').id
        form_view_id = self.env.ref('project.view_task_form2').id

        action = {'type': 'ir.actions.act_window_close'}
        project_task = self.task_ids.search([('project_id', '=', self.id)])
        portal_tasks = project_task.filtered(
            lambda task: task.partner_id in task.message_partner_ids)

        action = self.env.ref('project.action_view_task').read()[0]
        action['context'] = {}
        if len(portal_tasks) > 1:
            action['views'] = [[False, 'kanban'], [list_view_id, 'tree'], [
                form_view_id, 'form'], [False, 'graph'], [False, 'calendar'], [False, 'pivot']]
            action['domain'] = [('id', 'in', portal_tasks.ids)]
        elif len(portal_tasks) == 1:
            action['views'] = [(form_view_id, 'form')]
            action['res_id'] = portal_tasks.id
        action['display_name'] = 'Portal Tasks'
        action.setdefault('context', {})
        return action

    @api.model
    def create(self, vals):
        """
        Inherit create function to check privacy_visibility and add followers
        in project.
        :param vals:
        :return:
        """
        project = super(Project, self).create(vals)
        if project.privacy_visibility == 'followers' and project.partner_id:
            project.message_subscribe(project.partner_id.ids)
        return project

    def write(self, vals):
        """
        Inherit write function to check privacy_visibility and add followers
        in project.
        :param vals:
        :return:
        """
        if vals.get('partner_id') or vals.get('privacy_visibility'):
            for project in self.filtered(
                    lambda project: project.privacy_visibility == 'followers'):
                project.message_subscribe(project.partner_id.ids)
        return super(Project, self).write(vals)

    # from quotation module
    project_title = fields.Char(
        string="Project Title", readonly=True)

    def _compute_task_count(self):
        task_data = self.env[
            'project.task'].read_group(
            [('project_id', 'in', self.ids), ('parent_id', '=', False),
             '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)], ['project_id'], ['project_id'])
        result = dict((data['project_id'][0], data['project_id_count'])
                      for data in task_data)
        for project in self:
            project.task_count = result.get(project.id, 0)

    def action_open_project_process_wizard(self):
        view_id = self.env.ref(
            'project_process_manufacturing.view_project_process_wizard_form')
        return {
            'name': 'Create Process',
            'type': 'ir.actions.act_window',
            'view_id': view_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'create.project.process.wizard',
            'target': 'new',
            'context': {'default_finish_product_ids': self.finished_sale_line_ids.mapped('product_id').ids}

        }

    def generate_task_value(self, process_id, project_id, user_id, parent_id=False):
        """
        Create method to create task dictionary and return it
        :param project_process:
        :return:
        """

        date_deadline = fields.Date.to_string(
            datetime.now() + timedelta(process_id.task_validity_days))
        task_dict = {
            'name': process_id.name,
            'process_id': process_id.id,
            'project_id': project_id.id or False,
            'sale_type': project_id.sale_type or False,
            'project_size_id': project_id.project_size_id and project_id.project_size_id.id,
            'task_sequence': process_id.sequence,
            'user_id': user_id.id if user_id else False,
            'date_deadline': date_deadline,
        }
        return task_dict

    def generate_task(self, process):
        """This method  should  be  Generate Task for Specific Project."""
        Task = self.env['project.task']
        for prj_process in process:
            user_id = False
            if prj_process.user_id:
                user_id = prj_process.user_id
            task_dict = self.generate_task_value(
                prj_process.process_id, prj_process.project_id, user_id)
            task_id = Task.create(task_dict)
            if task_id and task_id.partner_id and not task_id.process_id.add_follower:
                task_id.message_unsubscribe([task_id.partner_id.id])
            if task_id:
                prj_process.write({
                    'task_id': task_id.id,
                })

    def action_inprogress(self):
        """
         This method  should  be set stages  in Project.
        """
        inprogess_stage_id = self.env.ref(
            'project_process_manufacturing.project_stage_inprogress').id
        for project in self:
            project.write({'stage_id': inprogess_stage_id,
                           'project_stage_visible': 'inprogress',
                           'date_confirm': datetime.now().date()})

    def action_cancel(self):
        for project in self:
            task_id = self.env['project.task'].search([
                ('project_id', '=', project.id),
                ('task_visible', 'not in', ('done', 'cancel'))
            ])
            if task_id:
                raise ValidationError(_(
                    "This Project can't be Cancel. To Cancel this Project before to Cancel Related Task"
                ))
            else:
                project.stage_id = self.env.ref(
                    'project_process_manufacturing.project_stage_cancel').id
                project.project_stage_visible = 'cancel'

    def action_done(self):
        for project in self:
            task_id = self.env['project.task'].search([
                ('project_id', '=', project.id),
                ('task_visible', 'not in', ('done', 'cancel'))
            ])
            if task_id:
                raise ValidationError(_(
                    "This Project can't be Done. To Done this Project before to Done Related Task"
                ))
            else:
                project.stage_id = self.env.ref(
                    'project_process_manufacturing.project_stage_done').id
                project.project_stage_visible = 'done'
                project.actual_done_date = datetime.now().date()
                project.next_toc_coc_date = datetime.now().date()

    def set_to_draft(self):
        for project in self:
            project.stage_id = self.env.ref(
                'project_process_manufacturing.project_stage_new').id
            project.project_stage_visible = 'new'

    def action_confirm(self):
        """
         This method should be Generate task and set stage in Project.
        """
        for project in self:
            if project.project_process_ids:
                project.generate_task(process=project.project_process_ids)
                project.action_inprogress()

    def _get_stage_name(self):
        for rec in self:
            rec.project_stage_name = self.stage_id.name

    def action_coc(self):
        self.stage_id = self.env.ref(
            'project_process_manufacturing.project_stage_coc').id
        self.coc_done = True

    def action_toc(self):
        self.stage_id = self.env.ref(
            'project_process_manufacturing.project_stage_toc').id
        self.toc_done = True

    def action_retention1(self):
        self.stage_id = self.env.ref(
            'project_process_manufacturing.project_stage_retention1').id

    def action_retention2(self):
        self.stage_id = self.env.ref(
            'project_process_manufacturing.project_stage_retention2').id


class ProjectType(models.Model):
    _name = 'project.stage'
    _description = 'Project Stage'
    _order = 'sequence'

    name = fields.Char('Stage Name', required=True, translate=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence')
    case_default = fields.Boolean(
        'Default for New Projects',
        help="If you check this field, this stage will be proposed by default on each new project. It will not assign this stage to existing projects.")
    fold = fields.Boolean(
        'Folded in Kanban View',
        help='This stage is folded in the kanban view when'
        'there are no records in that stage to display.')
