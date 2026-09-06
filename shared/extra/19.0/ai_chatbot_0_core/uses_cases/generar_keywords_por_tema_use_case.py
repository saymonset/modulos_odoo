# -*- coding: utf-8 -*-

import logging
import json
import re
from odoo import models, api

_logger = logging.getLogger(__name__)

_MAX_KEYWORDS = 10
_MIN_LEN = 4


class GenerarKeywordsPorTemaUseCase(models.TransientModel):
    _name = 'generar.keywords.por.tema.use.case'
    _description = 'Genera keywords específicas por tema del RAG'

    @api.model
    def execute(self, options):
        """Genera keywords específicas para cada tema del RAG.

        options: {titles: [str], openai_client, model, max_tokens}
        Devuelve: {titulo_normalizado: [str_keywords]} o dict vacío si falla.
        """
        titles = options.get('titles', [])
        openai_client = options.get('openai_client')
        model = options.get('model', 'gpt-3.5-turbo')
        max_tokens = options.get('max_tokens', 500)

        if not titles or not openai_client:
            return {}

        catalogo = "\n".join(f"- {t}" for t in titles)

        system_content = f"""
Eres un asistente que genera palabras clave para un chatbot de WhatsApp.

Dada la lista de temas de un negocio, genera EXACTAMENTE una lista de keywords
por tema. Las keywords deben ser:

1. ESPECÍFICAS del tema (nombres propios, medidas, características técnicas).
2. Palabras que un cliente usaría al preguntar por ese tema.
3. NUNCA incluir palabras genéricas como "qué", "tiene", "capacidad",
   "cuánto", "cuánto vale", "info", "información", "datos".
4. Entre 5 y {_MAX_KEYWORDS} keywords por tema.
5. Separadas por coma, sin espacios extra.

Ejemplo:
Tema: "Edificio de Oficinas 350 m²"
Keywords: edificio,oficinas,350,m²,galpón,piso,planta,data center,recepción,terraza

Tema: "Pan dulce artesanal"
Keywords: pan dulce,artesanal,concha,cuerno,oreja,poncha,garibaldi,precios,horario

Responde ÚNICAMENTE con un JSON válido:
{{
  "EDIFICIO DE OFICINAS 350 M²": "edificio,oficinas,350,m²,...",
  "OTRO TEMA": "keyword1,keyword2,..."
}}
"""

        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": "\n".join(titles)},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            data = json.loads(content)

            if not isinstance(data, dict):
                return {}

            # Normalizar claves y limpiar keywords
            resultado = {}
            for key, val in data.items():
                if not isinstance(key, str) or not isinstance(val, str):
                    continue
                kws = self._sanitizar_keywords(val)
                if kws:
                    resultado[key.upper().strip()] = kws
            return resultado

        except Exception as e:
            _logger.error(f"generar_keywords_por_tema: {e}")
            return {}

    @api.model
    def _sanitizar_keywords(self, keywords_str):
        """Limpia y valida una cadena de keywords separadas por coma."""
        if not keywords_str or not isinstance(keywords_str, str):
            return ''
        kws = []
        for kw in keywords_str.split(','):
            kw = kw.strip().lower()
            if len(kw) >= _MIN_LEN and kw not in _STOPWORDS_KEYWORDS:
                kws.append(kw)
            if len(kws) >= _MAX_KEYWORDS:
                break
        return ','.join(kws)


# Stopwords específicas para keywords (preguntas genéricas que no aportan)
_STOPWORDS_KEYWORDS = set("""
qué tiene cuanto como cual donde cuando porque cuanto
cuanta cuantos cuantas info información datos detalle
detalles descripcion descripción precio precios costo
costos valor valores servicio servicios producto productos
ayuda necesito quiero ver mostrar explicar decir hablar
""".split())
