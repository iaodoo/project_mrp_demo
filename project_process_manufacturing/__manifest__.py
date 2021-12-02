# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Project Process Manufacturing',
    'version': '13.0.1.0.1',
    'category': 'Project,MRP',
    'summary': 'Project Manufacturing',
    'description': """
       This module provide  below functionality:\n
       -> To create Manufacturing order's from the Project Process.
    """,
    'author': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': ['crm', 'sale_management', 'mrp_account', 'mrp_workorder', 'project','purchase', 'purchase_stock',
                'web_one2many_kanban','stock','mail', 'bista_project_folder_managment'],
    'data': [
        'security/groups_view.xml',
        'security/ir.model.access.csv',
        'data/project_stage_data.xml',
        'data/project_size_data.xml',
        'data/process_data.xml',
        'views/mail_templates.xml',
        'views/product_configurator_templates.xml',
        'views/res_config_settings_view.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_view.xml',
        'views/process_view.xml',
        'views/project_task_type_view.xml',
        'views/project_size_view.xml',
        'views/sale_order_view.xml',
        'views/product_view.xml',
        'views/project_mrp_view.xml',
        'wizard/procurement_order_request_view.xml',
        'views/purchase_order_view.xml',
        'views/project_task_view.xml',
        'views/project_view.xml',
        'views/mrp_workorder_view.xml',
        'views/mrp_workcenter_views.xml',
        'views/mrp_bom_views.xml',
        'views/project_view.xml',
        'wizard/mail_compose_message_view.xml',
        'wizard/stock_backorder_confirmation_views.xml',
        'wizard/create_production_wizard.xml',
        'wizard/wizard_product_attribute_process_view.xml',
        'views/project_portal_template.xml',
        'views/project_plan_view.xml',
        'report/purchase_order_templates.xml',
    ],
    'qweb': [
        'static/src/xml/composer.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
