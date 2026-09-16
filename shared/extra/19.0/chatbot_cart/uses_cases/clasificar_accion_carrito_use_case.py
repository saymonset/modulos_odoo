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
_PALABRAS_SALIR = {
    'salir', 'salirme', 'cancelar', 'abandonar', 'déjalo', 'dejalo',
    'menú principal', 'menu principal', 'volver', 'volver al menú',
    'volver al menu', 'dejar carrito', 'salir del carrito', 'salir del chat',
    'volver al negocio',
}
_PALABRAS_VACIAR = {'vaciar', 'quitar todo', 'eliminar todo', 'borrar todo', 'limpiar carrito'}
_PALABRAS_CONSULTAR = {'carrito', 'ver carrito', 'mi carrito', 'ver mi carrito', 'que tengo', 'qué tengo'}
_PALABRAS_CATALOGO = {
    'catálogo', 'catalogo', 'catálogo de productos', 'catalogo de productos',
    'que tienen', 'qué tienen', 'que venden', 'qué venden', 'que venden ustedes',
    'qué venden ustedes', 'que productos', 'qué productos', 'productos',
    'ver productos', 'muéstrame los productos', 'muestrame los productos',
    'lista de productos', 'listado de productos', 'productos disponibles',
    'catálogo por favor', 'catalogo por favor',
}
_PALABRAS_MAS = {'ver más', 'ver mas', 'más productos', 'mas productos', 'siguientes', 'siguiente'}
_PALABRAS_PAGAR = {'pagar', 'pago', 'finalizar', 'finalizar compra', 'proceder al pago', 'comprar',
                   'confirmar pedido', 'confirmar compra'}
_PALABRAS_COTIZACION = {
    'cotización', 'cotizacion', 'presupuesto', 'cotizar', 'cotización por favor',
    'cotiza', 'dame una cotización', 'dame cotización', 'quiero una cotización',
}
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

        Orden de prioridad (SPEC 33): el fallback determinista se consulta
        PRIMERO y gana para los comandos conocidos ("carrito", "catálogo",
        "más", "agrega N", etc.). La IA solo clasifica cuando el fallback no
        reconoce el mensaje (intención ambigua), evitando que la IA malclasifique
        comandos claros como "agrega 2".

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

        fallback, reconocido = self._clasificar_fallback(texto)
        if reconocido:
            return fallback

        if openai_client:
            try:
                return self._clasificar_con_ia(texto, openai_client, model, max_tokens)
            except Exception as e:
                _logger.error(f"Error clasificando acción de carrito con IA: {str(e)}")

        return fallback

    @api.model
    def _clasificar_con_ia(self, texto, openai_client, model, max_tokens):
        system_content = """
        Eres un asistente de carrito de compras. Clasifica el mensaje del usuario en UNA acción:

        - AGREGAR: quiere agregar un producto al carrito ("agrega 2 camisas rojas", "quiero 3 panes", "mete el chocolate").
        - QUITAR: quiere eliminar un producto del carrito ("quita la camisa", "elimina el pan").
        - MODIFICAR: quiere cambiar la cantidad de un producto ("cambia la camisa a 5", "pon 3 del chocolate").
        - CONSULTAR: quiere ver su carrito o resumen ("ver carrito", "qué tengo", "carrito").
        - BUSCAR: quiere buscar/ver productos sin agregarlos todavía ("muéstrame camisas", "qué venden").
        - CATALOGO: quiere ver el catálogo general de productos del negocio ("catálogo", "qué productos tienen", "qué venden", "productos", "catálogo de productos").
        - PAGAR: quiere pagar o finalizar la compra ("pagar", "finalizar compra").
        - COTIZACION: quiere una cotización/presupuesto sin pagar ahora
          ("cotización", "presupuesto", "cotiza", "no quiero pagar ahora",
          "quiero una cotización").
        - AYUDA: pide ayuda u opciones ("ayuda", "qué puedo hacer").
        - SALIR: quiere salir o cancelar del carrito para volver al negocio
          ("salir", "cancelar", "menú principal", "volver").
        - VACIAR: quiere vaciar todo el carrito ("vaciar carrito", "quitar todo").
        - FALLBACK: mensaje que NO es una operación del carrito ni pide ayuda
          (consultas del negocio, precios ajenos a la tienda, cortesía,
          off-topic como "¿cuánto cuesta una reparación?").

        REGLAS:
        - "quiero N producto" (sin verbo) es AGREGAR (ej. "quiero 2 camisas rojas").
        - "agrega N" o "agrega el N" con N número se refiere a un producto de la
          lista mostrada: es AGREGAR, NUNCA CATALOGO.
        - "más" o "ver más" tras ver productos es CATALOGO (siguiente página).
        - CATALOGO es SOLO cuando pide el catálogo general: "catálogo",
          "qué productos tienen", "qué venden", "productos". No confundas
          agregar un producto por su número con pedir el catálogo.
        - Un número suelto se interpreta como MODIFICAR cantidad si hay contexto de producto previo, si no como CONSULTAR.
        - Extrae el nombre del producto y la cantidad cuando sea posible.
        - Ante la duda entre una acción del carrito y algo fuera del carrito,
          prefiere FALLBACK: jamás inventes CONSULTAR para mensajes que no
          mencionan su carrito.

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
        """Extrae la cantidad del texto (número o palabra).

        SPEC 52: si el texto termina con 'a N' (cambiar X a 2), esa es la
        cantidad — evita tomar el '5' de un código '2.5'.
        """
        colas = re.search(r'\b[aà]\s*(\d{1,3})\s*(?:unidades?)?\s*$', texto)
        if colas:
            return int(colas.group(1))
        match = re.search(r'\b(\d+)\b', texto)
        if match:
            return int(match.group(1))
        for palabra, num in _VERBOS_CANTIDAD.items():
            if re.search(rf'\b{palabra}\b', texto):
                return num
        return 0

    @staticmethod
    def _clasificar_fallback(texto):
        """Clasificación determinista sin IA.

        Devuelve (resultado, reconocido): `reconocido` es True cuando el
        mensaje coincide con un comando conocido (la IA no debe sobre-escribirlo);
        False cuando el mensaje es ambiguo (la IA puede clasificarlo).
        """
        t = texto.lower().strip()
        cantidad = ClasificarAccionCarritoUseCase._extraer_cantidad(t)

        if any(p in t for p in _PALABRAS_VACIAR):
            return {"accion": "VACIAR", "producto": "", "cantidad": 0}, True
        if any(p in t for p in _PALABRAS_PAGAR):
            return {"accion": "PAGAR", "producto": "", "cantidad": 0}, True
        if any(p in t for p in _PALABRAS_COTIZACION):
            return {"accion": "COTIZACION", "producto": "", "cantidad": 0}, True
        if any(p in t for p in _PALABRAS_SALIR):
            return {"accion": "SALIR", "producto": "", "cantidad": 0}, True
        if any(p in t for p in _PALABRAS_AYUDA):
            return {"accion": "AYUDA", "producto": "", "cantidad": 0}, True
        if any(p in t for p in _PALABRAS_QUITAR):
            return {"accion": "QUITAR", "producto": t, "cantidad": cantidad}, True
        if any(p in t for p in _PALABRAS_MODIFICAR):
            return {"accion": "MODIFICAR", "producto": t, "cantidad": cantidad}, True
        if any(p in t for p in _PALABRAS_AGREGAR):
            return {"accion": "AGREGAR", "producto": t, "cantidad": cantidad}, True
        if any(p in t for p in _PALABRAS_CONSULTAR):
            return {"accion": "CONSULTAR", "producto": "", "cantidad": 0}, True
        if re.search(r'\b(ver\s+)?m[áa]s\b', t) or any(p in t for p in _PALABRAS_MAS):
            return {"accion": "CATALOGO", "producto": "MAS", "cantidad": 0}, True
        if any(p in t for p in _PALABRAS_CATALOGO):
            return {"accion": "CATALOGO", "producto": "", "cantidad": 0}, True

        tokens = set(re.findall(r'[a-záéíóúñü]+', t))
        if tokens & {'buscar', 'busca', 'muestrame', 'muéstrame', 'mostrar', 'lista', 'catalogo', 'catálogo'}:
            return {"accion": "BUSCAR", "producto": t, "cantidad": 0}, True

        return {"accion": "FALLBACK", "producto": "", "cantidad": 0}, False