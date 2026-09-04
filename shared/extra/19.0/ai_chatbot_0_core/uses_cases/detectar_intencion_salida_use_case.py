# -*- coding: utf-8 -*-

import logging
import json
import re
from odoo import models, api

_logger = logging.getLogger(__name__)

_PALABRAS_SALIDA = {
    'salir', 'cancelar', 'terminar', 'menu', 'menú', 'volver', 'atrás',
    'abortar', 'abandonar', 'déjalo', 'dejalo',
}
_FRASES_SALIDA = [
    'no quiero continuar', 'no deseo continuar', 'no quiero seguir', 'me voy',
]
_PALABRAS_DESVIO = {
    'precio', 'precios', 'costo', 'costos', 'cuanto', 'cuánto', 'dame',
    'dime', 'cómo', 'cuál', 'información', 'info', 'quién', 'quien', 'asesor',
}
_FRASES_DESVIO = [
    'hablar con', 'contactar', 'quiero saber', 'quiero hablar',
    'quiero que me', 'me puede', 'puedes decirme',
]
_PALABRAS_CONTROL = {
    'no', 'sí', 'si', 'listo', 'omitir', 'saltar', 'continuar', 'siguiente',
    'n', 'skip', 'no tengo', 'no la tengo', 'después', 'luego', 'finalizar',
    'terminar carga',
}


class DetectarIntencionSalidaUseCase(models.TransientModel):
    _name = 'detectar.intencion.salida.use.case'
    _description = 'Detecta si un mensaje del usuario expresa salida o desvío del flujo actual'

    @api.model
    def execute(self, options):
        """
        Clasifica el mensaje del usuario en respuesta, salida o desvío (pregunta
        fuera de flujo) en una única llamada IA, con fallback determinista.
        :param options: dict con:
            - 'texto_usuario': string
            - 'openai_client': cliente OpenAI
            - 'model': modelo a usar (ej. 'gpt-3.5-turbo')
            - 'max_tokens': opcional, default 100
        :return: dict con 'es_salida' (bool), 'es_desvio' (bool) y 'mensaje' (string)
        """
        texto = options.get('texto_usuario', '')
        openai_client = options.get('openai_client')
        model = options.get('model', 'gpt-3.5-turbo')
        max_tokens = options.get('max_tokens', 100)

        if not texto:
            _logger.error("No se proporcionó texto para clasificar")
            return {"es_salida": False, "es_desvio": False, "mensaje": ""}
        if not openai_client:
            _logger.error("No se proporcionó cliente de OpenAI")
            return self._clasificar_fallback(texto)

        try:
            system_content = """
            Eres un asistente que clasifica el mensaje del usuario dentro de un formulario guiado (túnel de registro con preguntas obligatorias).

            Clasifica el mensaje en UNA de estas tres categorías:
            - "respuesta": el usuario responde la pregunta actual (nombre, teléfono, 'sí'/'no', fechas, números, etc.). Las respuestas cortas y directas SIEMPRE son "respuesta", aunque mencionen una palabra como "precio" o "cuanto" (ej. "no", "sí", "Juan", "0412...", "15/05/1990").
            - "salida": el usuario quiere ABANDONAR o CANCELAR el proceso por completo (salir, cancelar, no quiero continuar, abandonar, déjalo, después lo hago).
            - "desvio": el usuario hace una pregunta o petición de información ajena al paso actual (ej. "¿cuánto cuesta?", "dame el precio", "¿cómo hago la cita?"). El desvío NO es una respuesta a la pregunta actual ni un abandono.

            REGLAS IMPORTANTES:
            - Solo marca "desvio" si el mensaje es claramente una pregunta o una petición explícita de información u otra acción ajena al paso actual.
            - Las respuestas cortas y plausibles para el paso actual NUNCA son "desvio" ni "salida" (ej. "sí", "no", "si", "listo", "omitir", "saltar", "continuar", un nombre, un número).
            - "no" como respuesta a un paso sí/no es "respuesta", jamás "salida".
            - Solo marca "salida" si el usuario explícitamente quiere detener el chatbot o irse.
            - Si el usuario dice que ha TERMINADO una acción (ej. "ya está", "listo", "ya terminé de subir las fotos"), eso es "respuesta", no "salida".

            Responde ÚNICAMENTE en formato JSON con la siguiente estructura:
            {"clasificacion": "respuesta"|"salida"|"desvio", "mensaje": "mensaje de despedida amigable si es salida, si no, cadena vacía"}
            """

            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": texto}
                ],
                max_tokens=max_tokens,
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            clasificacion = data.get("clasificacion", "respuesta")
            mensaje = data.get("mensaje", "")
            if clasificacion == "salida":
                return {"es_salida": True, "es_desvio": False, "mensaje": mensaje}
            if clasificacion == "desvio":
                return {"es_salida": False, "es_desvio": True, "mensaje": ""}
            return {"es_salida": False, "es_desvio": False, "mensaje": ""}

        except Exception as e:
            _logger.error(f"Error clasificando intención del mensaje: {str(e)}")
            return self._clasificar_fallback(texto)

    @staticmethod
    def _clasificar_fallback(texto):
        """Clasificación determinista sin IA. Matching por palabra exacta, sin
        substring ('no' como substring ya no marca salida)."""
        texto_lower = texto.lower().strip()
        if texto_lower in _PALABRAS_CONTROL:
            return {"es_salida": False, "es_desvio": False, "mensaje": ""}

        for frase in _FRASES_SALIDA:
            if frase in texto_lower:
                return {
                    "es_salida": True,
                    "es_desvio": False,
                    "mensaje": "Entendido. Si deseas continuar más tarde, aquí estaremos. ¡Hasta pronto!",
                }

        tokens = set(re.findall(r'[a-záéíóúñü]+', texto_lower))
        if tokens & _PALABRAS_SALIDA:
            return {
                "es_salida": True,
                "es_desvio": False,
                "mensaje": "Entendido. Si deseas continuar más tarde, aquí estaremos. ¡Hasta pronto!",
            }

        if '?' in texto or (tokens & _PALABRAS_DESVIO) or any(
                frase in texto_lower for frase in _FRASES_DESVIO):
            return {"es_salida": False, "es_desvio": True, "mensaje": ""}

        return {"es_salida": False, "es_desvio": False, "mensaje": ""}