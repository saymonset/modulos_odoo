# -*- coding: utf-8 -*-

import logging
import json
import re
from odoo import models, api

_logger = logging.getLogger(__name__)

_LABEL_MAX_LEN = 40


class GenerarMenuPorRolUseCase(models.TransientModel):
    _name = 'generar.menu.por.rol.use.case'
    _description = 'Genera encabezado y etiquetas del menú desde el rol del negocio'

    @api.model
    def execute(self, options):
        """Genera encabezado y etiquetas del menú adaptados al rol del negocio.

        :param options: dict con:
            - 'role_text': str, el contenido de chatbot.config.role (TÚ ERES)
            - 'brand_name': str, nombre de marca (opcional)
            - 'flujos_info': lista de dicts
              [{name, descripcion_intencion, label_actual}]
            - 'openai_client': cliente OpenAI
            - 'model': modelo a usar
            - 'max_tokens': opcional, default 300
        :return: dict {'header': str, 'labels': {flow_name: label}}
                 vacío si falla
        """
        role_text = options.get('role_text', '')
        brand_name = options.get('brand_name', '')
        flujos_info = options.get('flujos_info', [])
        openai_client = options.get('openai_client')
        model = options.get('model', 'gpt-3.5-turbo')
        max_tokens = options.get('max_tokens', 300)

        if not role_text or not flujos_info or not openai_client:
            _logger.error("Faltan parámetros para generar menú por rol")
            return {}

        catalogo = "\n".join(
            f"- {f.get('name')}: "
            f"{f.get('descripcion_intencion') or f.get('label_actual') or 'sin descripción'}"
            for f in flujos_info
        )

        brand_line = f"El nombre de marca del negocio es: {brand_name}." \
            if brand_name else "No se proporcionó nombre de marca."

        system_content = f"""
Eres un asistente que genera el menú principal de un chatbot de WhatsApp para
un negocio. Debes crear un saludo breve y una etiqueta por cada flujo.

{brand_line}

Catálogo de flujos (respeta EXACTAMENTE este orden y cantidad):
{catalogo}

REGLAS OBLIGATORIAS:
1. Genera un encabezado (header): un saludo breve que incluya el nombre de marca
   si se proporcionó, y una frase corta tipo "¿Qué necesitas hoy?".
   Máximo 1 línea, sin emojis al final.
2. Genera EXACTAMENTE una etiqueta por cada flujo, en el MISMO orden que el
   catálogo. NO agregues, quites ni reordenes flujos.
3. Cada etiqueta: máximo {_LABEL_MAX_LEN} caracteres, una línea, SIN números
   al inicio ni emojis. Ejemplo bueno: "Inmuebles y precios".
   Ejemplo malo: "1. Inmuebles" (tiene número) o "Inmuebles disponibles
   para venta 🏠" (tiene emoji).
4. Usa el lenguaje y vocabulario apropiado al rubro del negocio descrito en
   el rol. Ejemplo: inmobiliaria → "Inmuebles y cotizaciones";
   laboratorio → "Resultados de exámenes"; imprenta → "Servicios de impresión".
5. Sé conciso y directo. El usuario lee esto en WhatsApp.

Responde ÚNICAMENTE con un JSON válido con esta estructura:
{{
  "header": "Saludo breve con marca si aplica",
  "labels": {{
    "nombre_flujo_1": "Etiqueta del flujo 1",
    "nombre_flujo_2": "Etiqueta del flujo 2"
  }}
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
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            data = json.loads(content)

            header = self._sanitizar_header(data.get('header', ''))
            labels = self._sanitizar_labels(data.get('labels', {}))

            if not header or not labels:
                _logger.warning("generar_menu_por_rol: respuesta IA vacía")
                return {}

            return {'header': header, 'labels': labels}

        except Exception as e:
            _logger.error(f"Error en generar_menu_por_rol: {str(e)}")
            return {}

    @api.model
    def _sanitizar_header(self, header):
        """Limpia el header: una línea, sin saltos de carro extremos."""
        if not header or not isinstance(header, str):
            return ''
        header = header.strip()
        # Una sola línea: unir y quedarse con la primera
        header = re.split(r'[\n\r]+', header)[0].strip()
        return header

    @api.model
    def _sanitizar_labels(self, labels):
        """Limpia etiquetas: ≤40 chars, sin números/emojis iniciales."""
        if not labels or not isinstance(labels, dict):
            return {}
        cleaned = {}
        for key, val in labels.items():
            if not key or not isinstance(key, str) or not isinstance(val, str):
                continue
            label = val.strip()
            # Quitar números y puntos al inicio (ej. "1. Inmuebles")
            label = re.sub(r'^[\d\.\)\s]+', '', label).strip()
            # Quitar emojis al inicio
            label = re.sub(
                r'^[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u200d'
                r'\ufe0f\u20e3\U0001f600-\U0001f64f\U0001f300-\U0001f5ff'
                r'\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]+\s*',
                '', label
            ).strip()
            # Recortar a longitud máxima
            if len(label) > _LABEL_MAX_LEN:
                label = label[:_LABEL_MAX_LEN].rsplit(' ', 1)[0]
            if label:
                cleaned[key.strip()] = label
        return cleaned
