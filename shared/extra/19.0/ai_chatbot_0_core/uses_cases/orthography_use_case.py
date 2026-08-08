# -*- coding: utf-8 -*-

import logging
import json
from odoo import models, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class OrthographyUseCase(models.TransientModel):
    _name = 'orthography.use.case'
    _description = 'Orthography Check Use Case'

    @api.model
    def execute(self, options):
        """
        Ejecuta el caso de uso de verificación ortográfica
        :param options: Diccionario con opciones, debe contener 'prompt'
        :return: Diccionario con resultados
        """
        prompt = options.get('prompt', '')
        openai_client = options.get('openai_client')
        max_tokens = options.get('max_tokens', 150)
        model = options.get('model', 'gpt-3.5-turbo')  # Obtenemos el modelo de las opciones
        
        if not prompt:
            _logger.error("No se proporcionó un prompt para la verificación ortográfica")
            return {"error": "No se proporcionó un prompt"}
        if not openai_client:
            _logger.error("No se proporcionó el cliente de OpenAI")
            return {"error": "Configuración de OpenAI incorrecta"}
        
        try:
            # Crear el contenido del sistema con triple comillas
            system_content = """
            Te serán proveídos textos en español con posibles errores ortográficos y gramaticales,
            Las palabras usadas deben de existir en el diccionario de la Real Academia Española,
            Debes de responder en formato JSON, 
            tu tarea es corregirlos y retornar información soluciones, 
            también debes de dar un porcentaje de acierto por el usuario,

            Si no hay errores, debes de retornar un mensaje de felicitaciones.

            Ejemplo de salida:
            {
            "userScore": 0.95,
            "errors": ["error -> solución"],
            "message": "¡Felicidades, tu texto no tiene errores!"
            }
            """
            
            response = openai_client.chat.completions.create(
                model=model,  # Usamos el modelo desde las opciones
                messages=[
                    {
                        "role": "system", 
                        "content": system_content
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Obtener la respuesta y verificar si es válida
            response_content = response.choices[0].message.content
            
            # Intentar analizar la respuesta como JSON
            try:
                json_resp = json.loads(response_content)
            except json.JSONDecodeError as e:
                _logger.error(f"Respuesta de OpenAI no es JSON válido: {response_content}")
                # Si no es JSON válido, crear una respuesta de error
                json_resp = {
                    "userScore": 0,
                    "errors": ["Error en el formato de respuesta"],
                    "message": "Lo siento, hubo un error procesando tu texto.",
                    "IA": response_content
                }
            
            return {
                "case": prompt,
                "corrected_text": json_resp,
                "corrections": []
            }
            
        except Exception as e:
            _logger.error(f"Error al procesar la solicitud: {str(e)}")
            return {"error": f"Error en el procesamiento: {str(e)}"}