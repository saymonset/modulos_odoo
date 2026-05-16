# -*- coding: utf-8 -*-
import os
from pathlib import Path
import logging
import json
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

# 👇 Importa el caso de uso
from ..uses_cases.send_whatsapp_confirmation_use_case import SendWhatsappConfirmationUseCase

_logger = logging.getLogger(__name__)

class WhatsappService(models.AbstractModel):
    _name = 'whatsapp.service'
    _description = 'Whatsapp Service Layer'

    @api.model
    def sendWhatsappConfirmation(self, order):
        use_case = SendWhatsappConfirmationUseCase(self.env)
        return use_case.execute({'order': order})
    