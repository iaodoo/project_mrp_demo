# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

   	
   	@api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)


        return res