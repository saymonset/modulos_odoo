# -*- coding: utf-8 -*-
"""Redacción IA de los mensajes del carrito (SPEC 50).

El motor determinista decide la ACCIÓN; este servicio solo reescribe el
TEXTO que recibe el cliente como un vendedor humano. Si la IA no está
disponible o falla, devuelve la plantilla fija tal cual (fallback).
"""

import logging

from odoo.addons.chatbot_cart.services.prompt_carrito import redact_prompt_vendedor

_logger = logging.getLogger(__name__)

_TIMEOUT = 8
_MAX_TOKENS = 160
_TEMPERATURE = 0.5


def _hay_ia(env):
    """¿El negocio tiene IA (config + API key) disponible? (SPEC 50 paso 2)."""
    gpt = env['gpt.service'].sudo()
    try:
        return bool(gpt._get_openai_client(gpt._get_openai_config()))
    except Exception:
        return False


def redactar(env, plantilla_texto, contexto=None):
    """Redacta `plantilla_texto` como vendedor IA; fallback a la plantilla.

    `contexto`: dict con los DATOS REALES de la acción ya ejecutada
    (productos, precios, totales, botones sugeridos). La IA nunca inventa:
    solo reformula lo que el motor ejecutó.
    """
    if not plantilla_texto:
        return plantilla_texto
    contexto = contexto or {}
    try:
        gpt = env['gpt.service'].sudo()
        config = gpt._get_openai_config()
        client = gpt._get_openai_client(config)
        response = client.chat.completions.create(
            model=config.default_model,
            messages=[
                {'role': 'system', 'content': redact_prompt_vendedor()},
                {'role': 'user', 'content': (
                    "Contexto real de la acción ejecutada:\n"
                    f"{contexto}\n\n"
                    "Libreta fija (info que el motor generó):\n"
                    f"\"\"\"{plantilla_texto}\"\"\"\n\n"
                    "Reescribe la libreta como vendedor humano (reglas del system prompt)."
                )},
            ],
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            timeout=_TIMEOUT,
        )
        texto = (response.choices[0].message.content or '').strip()
        return texto or plantilla_texto
    except Exception as e:
        _logger.warning("Redacción IA del carrito no disponible, uso plantilla: %s", e)
        return plantilla_texto
