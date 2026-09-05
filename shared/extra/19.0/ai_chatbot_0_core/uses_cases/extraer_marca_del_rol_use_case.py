# -*- coding: utf-8 -*-

import logging
import json
import re
from odoo import models, api

_logger = logging.getLogger(__name__)

_BRAND_MAX_LEN = 60


class ExtraerMarcaDelRolUseCase(models.TransientModel):
    _name = 'extraer.marca.del.rol.use.case'
    _description = 'Extrae el nombre de la empresa desde el rol del negocio'

    @api.model
    def execute(self, options):
        """Extrae el nombre de marca (empresa) del rol del negocio.

        options debe contener: role_text (str), openai_client, model, max_tokens.

        Devuelve dict ``{'brand': str}`` con la marca extraída, o la marca
        determinista (patrón 'BOT X.') si la IA falla. Vacío si no hay rol.
        """
        role_text = options.get('role_text', '')
        openai_client = options.get('openai_client')
        model = options.get('model', 'gpt-3.5-turbo')
        max_tokens = options.get('max_tokens', 100)

        if not role_text or not openai_client:
            _logger.error("Faltan parámetros para extraer marca del rol")
            return {'brand': ''}

        system_content = f"""
Eres un asistente que identifica el nombre de la empresa/marca de un negocio
a partir de la descripción de su rol (sección "TÚ ERES").

Reglas:
1. Extrae ÚNICAMENTE el nombre de la empresa o marca (ej. "INMOBILIARIA KARLA
   CAMPOVERDE", "Ventas Sillas Paper", "IntegraIA"). No inventes ni añadas
   descripción ni rubro.
2. Si el texto menciona un nombre de empresa claro, úsalo tal cual aparece.
3. Si no hay un nombre claro, devuelve el sujeto principal que represente a la
   empresa.
4. Devuelve el nombre sin asteriscos, símbolos ni emojis.
5. Máximo {_BRAND_MAX_LEN} caracteres.

Responde ÚNICAMENTE con un JSON válido con esta estructura:
{{
  "brand": "Nombre de la empresa"
}}
"""

        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": role_text},
                ],
                max_tokens=max_tokens,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            brand = self._sanitizar_brand(data.get('brand', ''))
            if brand:
                return {'brand': brand}
            _logger.warning("extraer_marca_del_rol: respuesta IA vacía")
        except Exception as e:
            _logger.error(f"Error en extraer_marca_del_rol: {str(e)}")

        brand = self._extraer_marca_determinista(role_text)
        return {'brand': brand}

    @api.model
    def _sanitizar_brand(self, brand):
        """Limpia la marca: ≤60 chars, una línea, sin símbolos de negrita."""
        if not brand or not isinstance(brand, str):
            return ''
        brand = brand.strip()
        brand = re.sub(r'^[*_#]+|[*_#]+$', '', brand).strip()
        brand = re.split(r'[\n\r]+', brand)[0].strip()
        if len(brand) > _BRAND_MAX_LEN:
            brand = brand[:_BRAND_MAX_LEN].rsplit(' ', 1)[0]
        return brand

    @api.model
    def _extraer_marca_determinista(self, role_text):
        """Fallback determinista: patrón 'BOT X.' del rol."""
        for linea in (role_text or '').splitlines():
            m = re.match(r'\s*BOT\s+(.+?)\s*$', linea.strip(), re.IGNORECASE)
            if m:
                valor = re.split(r'[\.\,\n]', m.group(1))[0].strip()
                if valor:
                    return valor[:_BRAND_MAX_LEN]
        return ''
