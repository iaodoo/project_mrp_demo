# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

import os
import logging
_logger = logging.getLogger(__name__)

try:
    import paramiko
except ImportError:
    raise ImportError(
        'This module needs paramiko to automatically write backups to the FTP through SFTP. '
        'Please install paramiko on your system. (sudo pip3 install paramiko)')
from odoo import api, fields, models


class FolderDirectory(models.Model):
	_name = 'folder.directory'
	_description="Folder Directory"

	name = fields.Char(string="Folder Name")

	model_id = fields.Many2one(
		string='Model', comodel_name='ir.model')

	parent_id = fields.Many2one(
		string='Root Folder',comodel_name='folder.directory')

	directory_hierarchy = fields.Char(string="Directory Hierarchy",
		compute='_compute_directory_hierarchy')

	@api.depends('parent_id')
	def _compute_directory_hierarchy(self):
		"""
		Define the compute function _compute_directory_hierarchy to get Directory
		Directory Hierarchy.
		:return:
		"""
		for rec in self:
			rec.directory_hierarchy = '/' + str(rec.name)
			if rec.parent_id:
				rec.directory_hierarchy = '/'+ str(rec.parent_id.name) +  rec.directory_hierarchy
				if rec.parent_id.parent_id:
					rec.directory_hierarchy = '/'+ str(rec.parent_id.parent_id.name) + rec.directory_hierarchy
					if rec.parent_id.parent_id.parent_id:
						rec.directory_hierarchy = '/'+ str(rec.parent_id.parent_id.parent_id.name) + rec.directory_hierarchy


	def create_directory_structure(self,model_name, model_folder):
		sftp_config = self.env['sftp.configuration'].search([],limit=1)
		if sftp_config:
			if sftp_config.sftp_write:
				try:
					s = paramiko.SSHClient()
					s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
					s.connect(sftp_config.sftp_host, sftp_config.sftp_port, sftp_config.sftp_user, sftp_config.sftp_password, timeout=20)
					sftp = s.open_sftp()
					main_folder =  sftp_config.sftp_path+model_folder
					stdin, stdout, stderr = s.exec_command("echo '2l82c4ever' | sudo -S -k mkdir %s" %(main_folder))
					stdin.flush()
					for folder in self.search([('model_id.model','=',model_name)]):
						sub_folder = main_folder+folder.directory_hierarchy
						stdin, stdout, stderr = s.exec_command("echo '2l82c4ever' | sudo -S -k mkdir %s" %(sub_folder))
						stdin.flush()
				except Exception as error:
					_logger.critical('Error connecting to remote server! Error: ' + str(error))
			else:	
				if not os.path.isdir(sftp_config.root_folder):
					os.makedirs(sftp_config.root_folder)
				main_folder =  sftp_config.root_folder+ model_folder
				os.makedirs(main_folder)
				for folder in self.search([('model_id.model','=',model_name)]):
					sub_folder = main_folder+folder.directory_hierarchy
					if not os.path.isdir(sub_folder):
						os.makedirs(sub_folder)