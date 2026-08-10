# -*- coding: utf-8 -*-
"""Normalizador de prompt de negocio (PRON).

Alinea un PRON pegado por el cliente con el esquema de salida autoritativo de
10 campos (con flow_name) y con el campo de entrada real ('text') que n8n
envía al agente. Las reglas son idempotentes: aplicar la función dos veces
devuelve el mismo resultado. Nunca borra contenido de negocio.
"""
import re

_JSON_SCHEMA_9 = re.compile(
    r'("equipo_asignado"\s*:\s*"[^"]*"\s*,\s*)'
    r'(?!"flow_name"\s*:)'
    r'("session_id")'
)
_CLAVES_DASH = re.compile(
    r'(- equipo_asignado\s*)'
    r'(?!-- flow_name\s*)'
    r'(- session_id)'
)
_REGLA_FINAL = re.compile(
    r'(equipo_asignado,\s*)'
    r'(?!flow_name,\s*)'
    r'(session_id)'
)
_TEXT_NUEVE_CAMPOS = re.compile(r'\bde\s+9\s+campos\b')
_CAMPO_MESSAGE = re.compile(
    r'(-\s*)message(\s*-?\s*image_url)'
)


def normalizar_business_prompt(prompt_text):
    """Corrige un PRON de cliente para alinearlo con el formato de 10 campos.

    Devuelve una tupla (prompt_normalizado, cantidad_de_correcciones).
    Si el prompt no tiene esquema propio devuelve el texto sin cambios.
    """
    if not prompt_text:
        return prompt_text or '', 0

    cambios = 0
    texto = prompt_text

    def _apply(pattern, repl):
        nonlocal texto, cambios
        nuevo = pattern.sub(repl, texto)
        if nuevo != texto:
            cambios += 1
            return nuevo
        return texto

    texto = _apply(_JSON_SCHEMA_9, r'\1"flow_name": "", \2')
    texto = _apply(_CLAVES_DASH, r'\1- flow_name \2')
    texto = _apply(_REGLA_FINAL, r'\1flow_name, \2')
    texto = _apply(_TEXT_NUEVE_CAMPOS, 'de 10 campos')
    texto = _apply(_CAMPO_MESSAGE, r'\1text\2')

    return texto, cambios


# Marcadores estructurales que delimitaban líneas antes de que el campo
# fields.Char (obsoleto) aplanara el PRON a una sola línea.
_MARCADORES_RE = re.compile(
    r'(?<!\n)(===+ .*? ===+)|'          # secciones: === NOMBRE ===
    r'(?<!\n)(REGLA [A-ZÁÉÍÓÚÑ_]+:)|'   # cabeceras de regla
    r'(?<!\n)(PRIORIDAD \d+\b)|'        # PRIORIDAD N
    r'(?<!\n)(LÓGICA ESPECIAL)|'        # LÓGICA ESPECIAL PARA "SÍ"
    r'(?<!\n)(MENÚ MAESTRO)|'           # MENÚ MAESTRO
    r'(?<!\n)(RESPUESTAS POR REGLA)|'   # RESPUESTAS POR REGLA
    r'(?<!\n)(EJEMPLOS DE SALIDA)|'     # EJEMPLOS DE SALIDA
    r'(?<!\n)(CONSTRUCCIÓN FINAL)'      # CONSTRUCCIÓN FINAL
)
_EMOJI_NUM_RE = re.compile(r'(?<!\n)([0-9]+[️⃣])')


def reformatear_prompt_aplanado(prompt_text):
    """Restaura saltos de línea en un PRON aplanado por fields.Char.

    Heurístico para prompts que quedaron en una sola línea: inserta un salto
    antes de los marcadores estructurales típicos (===, REGLA, PRIORIDAD,
    LÓGICA ESPECIAL, MENÚ, EJEMPLOS, CONSTRUCCIÓN y números con emoji del menú).

    Devuelve (prompt_reformateado, cambios). Es seguro en prompts ya formateados:
    si hay varios saltos de línea, no toca nada.
    """
    if not prompt_text:
        return prompt_text or '', 0
    if prompt_text.count('\n') >= 5:
        return prompt_text, 0

    cambios = 0
    texto = prompt_text

    def _apply(pattern, repl):
        nonlocal texto, cambios
        nuevo = pattern.sub(repl, texto)
        if nuevo != texto:
            cambios += 1
            return nuevo
        return texto

    texto = _apply(_MARCADORES_RE, r'\n\1')
    texto = _apply(_EMOJI_NUM_RE, r'\n\1')

    return texto, cambios