# -*- coding: utf-8 -*-

import logging
import json
import re
from odoo import models, api

_logger = logging.getLogger(__name__)

_PALABRAS_AYUDA = {
    'ayuda', 'ayudame', 'opciones', 'menu', 'menú', 'qué puedo hacer', 'que puedo hacer',
    'instrucciones', 'como funciona', 'cómo funciona',
}
_PALABRAS_CANCELAR = {'cancelar', 'salir', 'salirme', 'abandonar', 'déjalo', 'dejalo'}
_PALABRAS_VACIAR = {'vaciar', 'quitar todo', 'eliminar todo', 'borrar todo', 'limpiar carrito'}
_PALABRAS_CONSULTAR = {'carrito', 'ver carrito', 'mi carrito', 'ver mi carrito', 'que tengo', 'qué tengo'}
_PALABRAS_PAGAR = {'pagar', 'pago', 'finalizar', 'finalizar compra', 'proceder al pago', 'comprar',
                   'confirmar pedido', 'confirmar compra'}
_PALABRAS_QUITAR = {'quitar', 'quita', 'eliminar', 'elimina', 'saca', 'remover', 'borrar', 'borra',
                    'quita del carrito'}
_PALABRAS_MODIFICAR = {'cambiar', 'cambia', 'modificar', 'modifica', 'poner', 'pon', 'cambia la cantidad'}
_PALABRAS_AGREGAR = {'agregar', 'agrega', 'añadir', 'añade', 'meter', 'mete', 'quiero', 'dame',
                     'quiero comprar', 'agregame', 'agregame al carrito'}

_VERBOS_CANTIDAD = {
    'uno': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
    'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
}


class ClasificarAccionCarritoUseCase(models.TransientModel):
    _name = 'clasificar.accion.carrito.use.case'
    _description = 'Clasifica el mensaje del usuario como acción del carrito'

    @api.model
    def execute(self, options):
        """Clasifica el mensaje en una acción de carrito con argumentos.

        :param options: dict con:
            - 'texto_usuario': string
            - 'openai_client': cliente OpenAI (opcional)
            - 'model': modelo a usar (opcional)
            - 'max_tokens': opcional
        :return: dict con 'accion', 'producto', 'cantidad'
        """
        texto = options.get('texto_usuario', '')
        openai_client = options.get('openai_client')
        model = options.get('model', 'gpt-3.5-turbo')
        max_tokens = options.get('max_tokens', 150)

        if not texto:
            return {"accion": "CONSULTAR", "producto": "", "cantidad": 0}

        if openai_client:
            try:
                return self._clasificar_con_ia(texto, openai_client, model, max_tokens)
            except Exception as e:
                _logger.error(f"Error clasificando acción de carrito con IA: {str(e)}")

        return self._clasificar_fallback(texto)

    @api.model
    def _clasificar_con_ia(self, texto, openai_client, model, max_tokens):
        system_content = """
        Eres un asistente de carrito de compras. Clasifica el mensaje del usuario en UNA acción:

        - AGREGAR: quiere agregar un producto al carrito ("agrega 2 camisas rojas", "quiero 3 panes", "mete el chocolate").
        - QUITAR: quiere eliminar un producto del carrito ("quita la camisa", "elimina el pan").
        - MODIFICAR: quiere cambiar la cantidad de un producto ("cambia la camisa a 5", "pon 3 del chocolate").
        - CONSULTAR: quiere ver su carrito o resumen ("ver carrito", "qué tengo", "carrito").
        - BUSCAR: quiere buscar/ver productos sin agregarlos todavía ("muéstrame camisas", "qué venden").
        - PAGAR: quiere pagar o finalizar la compra ("pagar", "finalizar compra").
        - AYUDA: pide ayuda u opciones ("ayuda", "qué puedo hacer").
        - CANCELAR: quiere cancelar o salir del carrito ("cancelar", "salir").
        - VACIAR: quiere vaciar todo el carrito ("vaciar carrito", "quitar todo").

        REGLAS:
        - "quiero N producto" (sin verbo) es AGREGAR (ej. "quiero 2 camisas rojas").
        - Un número suelto se interpreta como MODIFICAR cantidad si hay contexto de producto previo, si no como CONSULTAR.
        - Extrae el nombre del producto y la cantidad cuando sea posible.

        Responde ÚNICAMENTE JSON: {"accion": "...", "producto": "nombre del producto", "cantidad": n}
        """
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": texto}
            ],
            max_tokens=max_tokens,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        accion = str(data.get("accion", "CONSULTAR")).upper()
        producto = str(data.get("producto", "")).strip()
        try:
            cantidad = int(data.get("cantidad") or 0)
        except (TypeError, ValueError):
            cantidad = 0
        return {"accion": accion, "producto": producto, "cantidad": cantidad}

    @staticmethod
    def _extraer_cantidad(texto):
        """Extrae la cantidad del texto (número o palabra)."""
        match = re.search(r'\b(\d+)\b', texto)
        if match:
            return int(match.group(1))
        for palabra, num in _VERBOS_CANTIDAD.items():
            if re.search(rf'\b{palabra}\b', texto):
                return num
        return 0

    @staticmethod
    def _clasificar_fallback(texto):
        """Clasificación determinista sin IA."""
        t = texto.lower().strip()
        cantidad = ClasificarAccionCarritoUseCase._extraer_cantidad(t)

        if any(p in t for p in _PALABRAS_VACIAR):
            return {"accion": "VACIAR", "producto": "", "cantidad": 0}
        if any(p in t for p in _PALABRAS_PAGAR):
            return {"accion": "PAGAR", "producto": "", "cantidad": 0}
        if any(p in t for p in _PALABRAS_CANCELAR):
            return {"accion": "CANCELAR", "producto": "", "cantidad": 0}
        if any(p in t for p in _PALABRAS_AYUDA):
            return {"accion": "AYUDA", "producto": "", "cantidad": 0}
        if any(p in t for p in _PALABRAS_QUITAR):
            return {"accion": "QUITAR", "producto": t, "cantidad": cantidad}
        if any(p in t for p in _PALABRAS_MODIFICAR):
            return {"accion": "MODIFICAR", "producto": t, "cantidad": cantidad}
        if any(p in t for p in _PALABRAS_AGREGAR):
            return {"accion": "AGREGAR", "producto": t, "cantidad": cantidad}
        if any(p in t for p in _PALABRAS_CONSULTAR):
            return {"accion": "CONSULTAR", "producto": "", "cantidad": 0}

        tokens = set(re.findall(r'[a-záéíóúñü]+', t))
        if tokens & {'buscar', 'busca', 'muestrame', 'muéstrame', 'mostrar', 'ver', 'lista', 'catalogo', 'catálogo', 'que', 'qué'}:
            return {"accion": "BUSCAR", "producto": t, "cantidad": 0}

        return {"accion": "CONSULTAR", "producto": "", "cantidad": 0}