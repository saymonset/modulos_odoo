# -*- coding: utf-8 -*-

import logging
import json
from odoo import models, api

_logger = logging.getLogger(__name__)


class DetectarFlujosPromptUseCase(models.TransientModel):
    _name = 'detectar.flujos.prompt.use.case'
    _description = 'IA decide qué flujos de chatbot aplican según el prompt del negocio'

    @api.model
    def execute(self, options):
        """
        Dado el system_prompt del cliente y el catálogo de flujos con sus
        descripciones, devuelve qué flujos deberían estar activos.
        :param options: dict con:
            - 'prompt_text': string, el system_prompt del negocio
            - 'flujos_info': lista de dicts {name, descripcion_intencion, palabras_clave}
            - 'openai_client': cliente OpenAI
            - 'model': modelo a usar
            - 'max_tokens': opcional, default 300
        :return: lista de nombres de flujo que deben activarse
        """
        prompt_text = options.get('prompt_text', '')
        flujos_info = options.get('flujos_info', [])
        openai_client = options.get('openai_client')
        model = options.get('model', 'gpt-3.5-turbo')
        max_tokens = options.get('max_tokens', 300)

        if not prompt_text or not flujos_info or not openai_client:
            _logger.error("Faltan parámetros para detección de flujos por prompt")
            return []

        catalogo = "\n".join(
            f"- {f.get('name')}: {f.get('descripcion_intencion') or f.get('palabras_clave') or 'sin descripción'}"
            for f in flujos_info
        )

        system_content = f"""
Eres un asistente que determina qué flujos de chatbot necesita un negocio.

El catálogo de flujos disponibles es:
{catalogo}

Dado el prompt del negocio, decide cuáles de esos flujos aplican a ESE negocio
(y solo esos). Por ejemplo: un negocio de panadería no necesita flujos de
laboratorio clínico; un laboratorio no necesita flujos de venta de productos.

Reglas:
- Incluye SOLO los flujos que el negocio realmente va a usar.
- Si el negocio agenda citas, incluye los flujos de agendamiento/citas pertinentes.
- Si el negocio es de salud (clínica, hospital, laboratorio), incluye los flujos
  de citas médicas y resultados correspondientes.
- Si el negocio vende productos, incluye el flujo de ventas.
- El flujo 'flujo_agendamiento_default' se incluye siempre (es el fallback).

Responde ÚNICAMENTE con un JSON válido con esta estructura:
{{"flujos": ["flujo_1", "flujo_2"]}}
"""

        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt_text},
                ],
                max_tokens=max_tokens,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            flujos = data.get("flujos", [])
            return [f for f in flujos if isinstance(f, str)]
        except Exception as e:
            _logger.error(f"Error en detección de flujos por IA: {str(e)}")
            return []