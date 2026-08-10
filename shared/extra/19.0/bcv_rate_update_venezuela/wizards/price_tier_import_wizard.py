# -*- coding: utf-8 -*-
import base64
import logging
import os
import tempfile

import openpyxl

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIER_TYPES = {'retail', 'wholesale', 'mercadolibre'}

TIER_LABELS = {
    'retail': 'Menudeo',
    'wholesale': 'Mayoreo',
    'mercadolibre': 'MercadoLibre',
}


class PriceTierImportLog(models.TransientModel):
    _name = 'price.tier.import.log'
    _description = 'Log de importación de precios por nivel'

    wizard_id = fields.Many2one(
        'price.tier.import.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    default_code = fields.Char(string='Código')
    product_name = fields.Char(string='Producto')
    tier_type = fields.Char(string='Nivel')
    price_usd = fields.Float(string='Precio USD', digits=(12, 2))
    price_ves = fields.Float(string='Precio VES', digits=(12, 2))
    price_cop = fields.Float(string='Precio COP', digits=(12, 2))
    status = fields.Selection([
        ('created', 'Creado'),
        ('updated', 'Actualizado'),
        ('error', 'Error'),
    ], string='Estado')
    message = fields.Char(string='Mensaje')


class PriceTierImportWizard(models.TransientModel):
    _name = 'price.tier.import.wizard'
    _description = 'Importar precios por nivel desde Excel'

    file_data = fields.Binary(string='Archivo Excel', required=True)
    file_name = fields.Char(string='Nombre del archivo')
    state = fields.Selection([
        ('choose', 'Seleccionar archivo'),
        ('done', 'Importación completada'),
    ], default='choose', string='Estado')
    log_line_ids = fields.One2many(
        'price.tier.import.log',
        'wizard_id',
        string='Resultados',
    )

    def _parse_excel(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError('Debe seleccionar un archivo Excel.')

        decoded = base64.b64decode(self.file_data)
        suffix = os.path.splitext(self.file_name or '.xlsx')[1] or '.xlsx'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(decoded)
            tmp_path = tmp.name

        try:
            wb = openpyxl.load_workbook(tmp_path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
        finally:
            os.unlink(tmp_path)

        if not rows:
            raise UserError('El archivo Excel está vacío.')

        headers = [str(h).strip().lower() if h is not None else '' for h in rows[0]]
        required = {'default_code', 'tier_type', 'price_usd'}
        missing = required - set(headers)
        if missing:
            raise UserError(
                'El archivo debe tener las columnas: default_code, tier_type, price_usd.\n'
                'Columnas encontradas: %s\n'
                'Faltan: %s' % (', '.join(headers), ', '.join(missing))
            )

        results = []
        for row in rows[1:]:
            if not any(cell is not None for cell in row):
                continue
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else None
            results.append(row_dict)

        if not results:
            raise UserError('El archivo no contiene datos después del encabezado.')

        return results

    def _find_template(self, default_code):
        if not default_code:
            return None
        code = str(default_code).strip()
        if not code:
            return None
        return self.env['product.template'].search([
            ('default_code', '=', code),
        ], limit=1)

    def _upsert_tier(self, template, tier_type, price_usd):
        existing = self.env['product.price.tier'].search([
            ('product_tmpl_id', '=', template.id),
            ('tier_type', '=', tier_type),
        ], limit=1)

        if existing:
            existing.write({'price_usd': price_usd})
            return existing, 'updated'
        else:
            new = self.env['product.price.tier'].create({
                'product_tmpl_id': template.id,
                'tier_type': tier_type,
                'price_usd': price_usd,
            })
            return new, 'created'

    def action_import(self):
        self.ensure_one()
        rows = self._parse_excel()

        log_vals_list = []

        for row in rows:
            default_code = row.get('default_code')
            tier_type_raw = row.get('tier_type')
            price_usd_raw = row.get('price_usd')

            try:
                # --- default_code ---
                code = str(default_code).strip() if default_code else ''
                if not code:
                    raise ValueError('default_code vacío')

                template = self._find_template(code)
                if not template:
                    raise ValueError("No se encontró producto con código '%s'" % code)

                # --- tier_type ---
                tier_type = str(tier_type_raw).strip().lower() if tier_type_raw else ''
                if tier_type not in TIER_TYPES:
                    raise ValueError(
                        "tier_type inválido '%s'. Debe ser: retail, wholesale o mercadolibre"
                        % tier_type
                    )

                # --- price_usd ---
                try:
                    price_usd = float(price_usd_raw) if price_usd_raw not in (None, '', False) else 0.0
                except (TypeError, ValueError):
                    raise ValueError("price_usd inválido: '%s'" % price_usd_raw)

                if price_usd <= 0:
                    raise ValueError("price_usd debe ser mayor a 0, obtenido: %s" % price_usd)

                # --- upsert ---
                tier, status = self._upsert_tier(template, tier_type, price_usd)

                log_vals_list.append({
                    'wizard_id': self.id,
                    'default_code': code,
                    'product_name': template.name,
                    'tier_type': TIER_LABELS.get(tier_type, tier_type),
                    'price_usd': tier.price_usd,
                    'price_ves': tier.price_ves,
                    'price_cop': tier.price_cop,
                    'status': status,
                    'message': 'Creado' if status == 'created' else 'Actualizado',
                })

            except Exception as e:
                _logger.warning('Error importando default_code=%s: %s', default_code, e)
                log_vals_list.append({
                    'wizard_id': self.id,
                    'default_code': str(default_code or '').strip(),
                    'product_name': '',
                    'tier_type': str(tier_type_raw or '').strip(),
                    'price_usd': 0.0,
                    'price_ves': 0.0,
                    'price_cop': 0.0,
                    'status': 'error',
                    'message': str(e),
                })

        if log_vals_list:
            self.env['price.tier.import.log'].create(log_vals_list)

        self.state = 'done'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'price.tier.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
