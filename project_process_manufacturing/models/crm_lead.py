# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class Lead(models.Model):
    _inherit = "crm.lead"

    fax = fields.Char(string="Fax")
    custom_create_date = fields.Datetime(
        string='Custom create date',
        required=False,
        readonly=False,
        index=False,
        help=False
    )

