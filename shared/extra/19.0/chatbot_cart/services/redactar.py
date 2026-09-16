# -*- coding: utf-8 -*-
"""Redacción IA de los mensajes del carrito (SPEC 50).

El motor determinista decide la ACCIÓN; este servicio solo reescribe el
TEXTO que recibe el cliente como un vendedor humano. Si la IA no está
disponible o falla, devuelve la plantilla fija tal cual (fallback).
"""

import logging
import re

from odoo.addons.chatbot_cart.services.prompt_carrito import redact_prompt_vendedor

_logger = logging.getLogger(__name__)

_TIMEOUT = 8
_MAX_TOKENS = 160
_TEMPERATURE = 0.5

# SPEC 51: la IA no puede fugar instrucciones del router ni formato crudo.
_FUGA_RE = re.compile(
    r'^.*(?:flow_name\s*=|equipo_asignado\s*=|__flow__|"\s*accion\s*":).*$',
    re.IGNORECASE)


def _sanitizar(texto):
    """Elimina fugas de instrucciones internas, JSON crudo y markdown.

    Devuelve None si tras limpiar no queda texto legible (caller usa la
    plantilla original).
    """
    if not texto:
        return None
    # quitar bloque de código markdown completo
    texto = re.sub(r'```.*?```', '', texto, flags=re.DOTALL)
    lineas = [
        ln for ln in texto.split('\n')
        if not _FUGA_RE.match(ln.strip())
        and ln.strip() not in {'{', '}', '[', ']'}
    ]
    limpio = '\n'.join(lineas).strip()
    if len(re.sub(r'[^A-Za-zÁÉÍÓÚáéíóúñÑ¿¡!.,:; ]', '', limpio)) < 12:
        return None
    return limpio


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
        texto = _sanitizar((response.choices[0].message.content or '').strip())
        return texto or plantilla_texto
    except Exception as e:
        _logger.warning("Redacción IA del carrito no disponible, uso plantilla: %s", e)
        return plantilla_texto
