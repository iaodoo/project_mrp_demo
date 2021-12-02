# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Bista Project Folder Management",
    'category': 'Project/FOlder',
    'summary': "Bista Project FOlder Management",
    'description': """
Project SubTasks,
===================================================================
    *This module is used for Create Folder Structure For Project and Task.
    """,
    'version': '13.0.1.0.0',
    'author': 'Bista Solutions Pvt. Ltd.',
    'website': 'https://www.bistasolutions.com',
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    'depends': ['base','project','sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/sftp_configuration_view.xml',
        'views/folder_directory_view.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
