# -*- coding: utf-8 -*-

import logging
import json
from odoo import models, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class GenerarPreguntaIntegraiaUseCase(models.TransientModel):
    _name = 'generar_pregunta_integraia.use.case'
    _description = 'generar_pregunta_integraia_use_case - Genera preguntas amigables a partir de un campo'

    @api.model
    def execute(self, options):
        """
        Ejecuta el caso de uso para generar una pregunta amigable basada en el prompt.
        :param options: Diccionario con opciones, debe contener 'prompt' (ej: "Teléfono")
        :return: Diccionario con la pregunta generada y otros metadatos
        """
        prompt = options.get('prompt', '')
        openai_client = options.get('openai_client')
        max_tokens = options.get('max_tokens', 150)
        model = options.get('model', 'gpt-3.5-turbo')

        if not prompt:
            _logger.error("No se proporcionó un prompt (nombre_mostrar) para generar la pregunta")
            return {"error": "No se proporcionó un prompt"}
        if not openai_client:
            _logger.error("No se proporcionó el cliente de OpenAI")
            return {"error": "Configuración de OpenAI incorrecta"}

        try:
            system_content = """
                Eres un asistente experto en crear preguntas amigables y naturales para un chatbot de atención al cliente.

                Recibirás el nombre de un campo (ej: "Teléfono", "Nombre completo", "Consentimiento WhatsApp", "Correo electrónico") y debes generar una pregunta cálida, breve (máximo 2 frases) y adaptada al contexto.

                **Reglas importantes según el tipo de campo (aunque no se te indique explícitamente, infiere por el nombre):**

                - Si el campo es **booleano (sí/no)**, por ejemplo "Consentimiento WhatsApp", la pregunta debe pedir **claramente "sí" o "no"**. Ejemplo: "Para poder enviarte recordatorios por WhatsApp, necesito tu autorización. ¿Me dices 'sí' o 'no'? 😊"
                - Si el campo es **opcional** (por ejemplo "Correo electrónico"), la pregunta debe ofrecer la opción de omitir. Ejemplo: "Si deseas, puedes dejarme tu correo electrónico para enviarte información adicional. Si no quieres, escribe 'omitir' ✉️"
                - Para **teléfono**: "¡Hola! Para empezar, ¿me compartes tu número de teléfono? Así podré ayudarte mejor 📱"
                - Para **nombre completo**: "Cuéntame, ¿cuál es tu nombre completo? Me gustaría saber cómo llamarte 😊"
                - Para **cédula**: "¿Podrías indicarme tu número de cédula? Es importante para tu ficha médica."
                - Para **fecha de nacimiento**: "¿Cuál es tu fecha de nacimiento? Por favor, escríbela en formato día/mes/año, por ejemplo 15/05/1990."

                **Formato de respuesta:** Debes responder ÚNICAMENTE con un JSON válido como este:
                {"pregunta_amigable": "texto de la pregunta"}

                No incluyas nada más fuera del JSON. Usa un tono cordial, empático y cercano. Puedes usar emojis suaves (😊, 📱, ✉️) pero sin abusar.
                """

            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.5,
                response_format={"type": "json_object"}
            )

            response_content = response.choices[0].message.content

            try:
                json_resp = json.loads(response_content)
                generated_question = json_resp.get("pregunta_amigable", "")
                if not generated_question:
                    raise ValueError("No se encontró 'pregunta_amigable' en la respuesta")
            except (json.JSONDecodeError, ValueError) as e:
                _logger.error(f"Respuesta inválida de OpenAI: {response_content}")
                # Fallback: generar una pregunta por defecto
                generated_question = f"Por favor, ingresa tu {prompt.lower()}"

            return {
                "original_prompt": prompt,
                "generated_question": generated_question,
                "status": "success"
            }

        except Exception as e:
            _logger.error(f"Error al generar la pregunta: {str(e)}")
            return {"error": f"Error en el procesamiento: {str(e)}"}