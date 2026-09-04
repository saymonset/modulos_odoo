# -*- coding: utf-8 -*-
"""Mensajes de validación amigables compartidos por los validadores del chatbot.

Viven en ai_chatbot_0_core (base) para que ai_chatbot_1_portal los importe sin
romper la dirección de dependencias.
"""

MENSAJES_VALIDACION = {
    "phone_empty": "El teléfono no puede estar vacío. Escríbelo con su código de área.",
    "phone_digits": "El teléfono debe contener al menos un número.",
    "phone_short": "El número parece muy corto. Escríbelo completo con su código de área. Ejemplo: 04121234567",
    "phone_long": "El número es demasiado largo. Verifica que esté bien escrito. Ejemplo: 04121234567",
    "phone_invalid": "Ese número no parece válido. Escríbelo completo con su código de área. Ejemplo: 04121234567",
    "boolean": "No entendí tu respuesta. Por favor, responde solo 'sí' o 'no'.",
    "integer": "Necesito un número entero, sin letras ni decimales. Ejemplo: 2",
    "float": "Necesito un número con decimales. Ejemplo: 1.5",
    "date": "No reconocí la fecha. Escríbela como día/mes/año. Ejemplo: 15/05/1990",
    "datetime": "No reconocí la fecha y hora. Escríbela como día/mes/año y hora. Ejemplo: 15/05/1990 10:30",
    "image_empty": "No recibí ninguna imagen. Envíala o escribe 'saltar' para omitir este paso.",
    "image_url": "El enlace que enviaste no parece una imagen válida. Envía la foto o escribe 'saltar' para omitir este paso.",
    "unsupported": "No pude procesar ese tipo de dato. Intenta responder de otra manera.",
}