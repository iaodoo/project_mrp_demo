# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

import os
import datetime
import time
import socket
from reportlab.pdfgen.canvas import Canvas

from odoo import models, fields, api, tools, _
from odoo.exceptions import Warning, UserError
import odoo

import logging
_logger = logging.getLogger(__name__)
import shutil
import json
import tempfile
from odoo.exceptions import AccessDenied


try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib


try:
    import paramiko
except ImportError:
    raise ImportError(
        'This module needs paramiko to automatically write backups to the FTP through SFTP. '
        'Please install paramiko on your system. (sudo pip3 install paramiko)')


from odoo import models, fields, api


class SftpConfiguration(models.Model):
    _name = 'sftp.configuration'
    _description = "SFTP Configuration"

    name = fields.Char('name')
    host = fields.Char('Host')
    port = fields.Char('Port', required=True, default=8069)
    active = fields.Boolean('Active',default=True)
    root_folder = fields.Char('Root Directory')
    sftp_write = fields.Boolean('Root Directory to external server with sftp',
                                help="If you check this option you can specify the details needed to write to a remote "
                                "server with SFTP.")
    sftp_path = fields.Char('Path external server',
                            help='The location to the folder where the dumps should be written to. For example '
                            '/odoo/backups/.\nFiles will then be written to /odoo/backups/ on your remote server.')
    sftp_host = fields.Char('IP Address SFTP Server',
                            help='The IP address from your remote server. For example 192.168.0.1')
    sftp_port = fields.Integer(
        'SFTP Port', help='The port on the FTP server that accepts SSH/SFTP calls.', default=22)
    sftp_user = fields.Char('Username SFTP Server',
                            help='The username where the SFTP connection should be made with. This is the user on the '
                            'external server.')
    sftp_password = fields.Char('Password User SFTP Server',
                                help='The password from the user where the SFTP connection should be made with. This '
                                'is the password from the user on the external server.')

    def test_create_file(self):
        file_name = "test_191"
        if not self.sftp_write:
            file_path = self.root_folder or ""
            self.create_pdf_file(
                file_path=file_path, file_name=file_name)
            raise Warning("Create file on Local Server ScucessFully!")
        else:
            self.create_pdf_file(
                file_path='/tmp', file_name=file_name)
            tmp_path = '/tmp/'+file_name+'.pdf'
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.sftp_host, self.sftp_port, self.sftp_user, self.sftp_password, timeout=20)
            ssh_client = ssh.open_sftp()
            ssh_client.put(tmp_path,tmp_path)
            stdin, stdout, stderr = ssh.exec_command("echo %s | sudo -S -k mv %s %s" %(self.sftp_password,tmp_path,self.sftp_path))
            stdin.flush()
            raise Warning("Create file on Remote Server ScucessFully!")
        return True

    def create_file_remote_server(self,filename):
        self.create_pdf_file(
            file_path='/tmp', file_name=filename)
        try:
            filename = filename+'.pdf'
            tmp_path = '/tmp/'+filename
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.sftp_host, self.sftp_port, self.sftp_user, self.sftp_password, timeout=20)
            ssh_client = ssh.open_sftp()
            ssh_client.put(tmp_path,tmp_path)
            stdin, stdout, stderr = ssh.exec_command("echo %s | sudo -S -k mv %s %s" %(self.sftp_password,tmp_path,self.sftp_path))
            stdin.flush()
        except Exception as e:
            raise Warning('There was a problem connecting to the remote ftp Server: ' + str(e))
        return True

    def test_sftp_connection(self, context=None):
        self.ensure_one()

        # Check if there is a success or fail and write messages
        message_title = ""
        message_content = ""
        error = ""
        has_failed = False

        for rec in self:
            path_to_write_to = rec.sftp_path
            ip_host = rec.sftp_host
            port_host = rec.sftp_port
            username_login = rec.sftp_user
            password_login = rec.sftp_password

            # Connect with external server over SFTP, so we know sure that
            # everything works.
            try:
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(ip_host, port_host, username_login,
                          password_login, timeout=10)
                sftp = s.open_sftp()
                message_title = _(
                    "Connection Test Succeeded!\nEverything seems properly set up for FTP back-ups!")
            except Exception as e:
                _logger.critical(
                    'There was a problem connecting to the remote ftp: ' + str(e))
                error += str(e)
                has_failed = True
                message_title = _("Connection Test Failed!")
                if len(rec.sftp_host) < 8:
                    message_content += "\nYour IP address seems to be too short.\n"
                message_content += _("Here is what we got instead:\n")
            finally:
                if s:
                    s.close()

        if has_failed:
            raise Warning(message_title + '\n\n' +
                          message_content + "%s" % str(error))
        else:
            raise Warning(message_title + '\n\n' + message_content)

    def create_pdf_file(self, file_path, file_name):
        """
        Create pdf blank file using filepath and filename.
        :param file_path:
        :param file_name:
        :return:
        """
        if file_path and file_name:
            full_path = file_path + '/' + file_name + '.pdf'
            try:
                canvas = Canvas(full_path)
                canvas.showPage()
                canvas.save()
            except UserError as error:
                raise UserError(error)
        else:
            raise UserError(
                "FilePath or FileName is not retrieve please set it properly")
