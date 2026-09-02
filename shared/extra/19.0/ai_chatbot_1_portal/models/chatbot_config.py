import logging
import re
import unicodedata

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

_STOPWORDS = set("""
de la el los las y o u a en para por con un una unos unas al del que como es son se
su sus este esta estos estas lo le les me nos mi mis tu tus no si pero ni muy mas
menos ya luego bien desde hasta sobre entre segun tras contra hacia bajo cuando
donde como cual cuales quien quienes cuanto cuanta cuantos cuantas aquel aquella
aquellos aquellas nuestro nuestra nuestros nuestras vuestro vuestra vuestros
vuestras os le les la lo las los uno una unos
""".split())


def _es_encabezado(linea):
    if not linea or len(linea) > 60:
        return False
    if linea.endswith(':'):
        return True
    t = linea.lstrip('-•* ').strip()
    return len(t.split()) >= 2 and t.isupper()


def _nombre_desde_chunk(chunk, indice):
    for linea in chunk.splitlines():
        l = linea.strip()
        if l.endswith(':'):
            return l.rstrip(':').strip()[:30] or 'SECCION_%d' % indice
    for linea in chunk.splitlines():
        l = linea.strip()
        if l and len(l) <= 40:
            return l[:30]
    return 'SECCION_%d' % indice


def _normalizar(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', (texto or '').upper())
        if unicodedata.category(c) != 'Mn')


def _es_seccion_role(nombre):
    n = _normalizar(nombre)
    return n in ('TU ERES', 'OBJETIVO') or n.startswith('REGLA')


def _detectar_secciones(filas):
    secciones = []
    por_archivo = {}
    for file_id, texto in filas:
        por_archivo.setdefault(file_id, []).append(texto or '')
    for chunks in por_archivo.values():
        texto = "\n\n".join(chunks)
        lineas = texto.splitlines()
        actual = None
        buf = []
        for linea in lineas:
            t = linea.strip()
            if _es_encabezado(t):
                if actual:
                    secciones.append((actual, "\n".join(buf).strip()))
                actual = t.rstrip(':').strip()
                buf = [linea]
            else:
                buf.append(linea)
        if actual:
            secciones.append((actual, "\n".join(buf).strip()))
        else:
            for i, chunk in enumerate(chunks, 1):
                secciones.append((_nombre_desde_chunk(chunk, i), chunk.strip()))
    return [s for s in secciones if s[1]]


def _extract_keywords(texto, limite=12):
    palabras = re.findall(r'[a-záéíóúüñ]+', texto.lower())
    de_precio = set()
    for m in re.finditer(r'\$\s*[\d.]+', texto):
        ctx = re.findall(
            r'[a-záéíóúüñ]+', texto[max(0, m.start() - 30):m.start()].lower())
        de_precio.update(ctx[-2:])
    conteo = {}
    for p in palabras:
        if len(p) >= 3 and p not in _STOPWORDS:
            conteo[p] = conteo.get(p, 0) + 1
    orden = sorted(conteo, key=lambda p: (p not in de_precio, -conteo[p]))
    salida = []
    for p in orden:
        if p not in salida:
            salida.append(p)
        if len(salida) >= limite:
            break
    return ",".join(salida)


# Intenciones "sistema" que el bot necesita para operar (menú, cancelar, salir,
# fallback y las que disparan flujos). Se generan desde las secciones del RAG
# cuando existen y, si faltan, quedan como ranuras vacías para que el humano las
# complete (pinceladas). El contenido nunca trae marca de una demo.
_SYSTEM_INTENCIONES = {
    'MENU': {
        'nombre': 'MENU', 'keywords': 'menu,menu_principal,menú,opciones,ayuda',
        'prioridad': 10, 'es_menu': True, 'tipo_pregunta': '',
    },
    'CANCELAR': {
        'nombre': 'CANCELAR', 'keywords': 'cancelar',
        'prioridad': 11, 'es_menu': False, 'tipo_pregunta': '',
    },
    'SALIR': {
        'nombre': 'SALIR', 'keywords': 'salir,gracias,muchas gracias',
        'prioridad': 30, 'es_menu': False, 'tipo_pregunta': '',
    },
    'CITA_DIRECTA': {
        'nombre': 'CITA_DIRECTA',
        'keywords': ('demo,cita,reunión,agendar,asesoría,quiero que me llamen,'
                     'hablar con alguien,presentación,contactar,asesor'),
        'prioridad': 42, 'es_menu': False, 'tipo_pregunta': 'CITA_DIRECTA',
    },
    'OTRA_CONSULTA': {
        'nombre': 'OTRA_CONSULTA',
        'keywords': ('desarrollo a medida,personalizado,módulo,integración,api,'
                     'migración,conectar sistemas,adaptar odoo,modificar odoo,'
                     'programación,python,angular,react,proyecto'),
        'prioridad': 44, 'es_menu': False, 'tipo_pregunta': 'OTRA_CONSULTA',
    },
    'CONFIRMACION': {
        'nombre': 'CONFIRMACION',
        'keywords': 'confirmar,confirmo,sí,si,registrar solicitud',
        'prioridad': 50, 'es_menu': False, 'tipo_pregunta': 'CONFIRMACION',
    },
    'CONFIRMACION_IMAGEN': {
        'nombre': 'CONFIRMACION_IMAGEN',
        'keywords': ('imagen,archivo,foto,comprobante,documento,logo,evidencia,'
                     'captura,adjunto'),
        'prioridad': 52, 'es_menu': False, 'tipo_pregunta': 'CONFIRMACION_IMAGEN',
        'output_default': ('¡Recibí tu imagen/archivo! 📎 ¿Quieres que la revise '
                           'un asesor y te contacte? Responde SÍ o NO.'),
    },
    'IMAGEN': {
        'nombre': 'IMAGEN',
        'keywords': 'enviar archivo,te envío,adjunto,aquí está,te mando',
        'prioridad': 53, 'es_menu': False, 'tipo_pregunta': 'IMAGEN',
        'output_default': ('¡Perfecto! Voy a canalizar tu archivo con el '
                           'departamento correspondiente. Te haré unas breves '
                           'preguntas. (flujo_resultados_imagenes)'),
    },
    'FALLBACK': {
        'nombre': 'FALLBACK', 'keywords': '', 'prioridad': 99,
        'es_menu': False, 'tipo_pregunta': '',
        'output_default': ('Disculpa, no entendí 🤔 ¿Puedes reformularlo? '
                           'Escribe *menu* para ver las opciones.'),
    },
}

# Ranuras esenciales que siempre se crean (vacías si el RAG no las trae).
# Incluye las de manejo de imágenes/archivos: todo cliente puede enviar fotos,
# logos o comprobantes por WhatsApp, así que sus intenciones y flujo deben
# existir siempre.
_BASE_SISTEMA = (
    'MENU', 'CANCELAR', 'SALIR', 'FALLBACK',
    'IMAGEN', 'CONFIRMACION_IMAGEN',
)


class ChatbotConfig(models.Model):
    _name = "chatbot.config"
    _description = "Configuración de negocio del chatbot"

    name = fields.Char(string="Nombre del negocio", required=True)
    role = fields.Text(
        string="Rol / objetivo",
        help='"TÚ ERES" / objetivo de venta del agente para este negocio.',
    )
    cta_url = fields.Char(
        string="URL de llamada a la acción",
        help='Web del negocio (ej. integraia.lat).',
    )
    contacto = fields.Text(
        string="Contacto",
        help='Teléfono, horario, email de contacto del negocio.',
    )
    bloque_conocimiento = fields.Text(
        string="Base de conocimiento",
        help='Conocimiento libre del negocio (precios, servicios, requisitos, políticas).',
    )
    intencion_ids = fields.One2many(
        "chatbot.intencion",
        "config_id",
        string="Intenciones",
        copy=True,
    )
    flujo_ids = fields.Many2many(
        "chatbot.flujo",
        string="Flujos de este cliente (marca los que aplican)",
        help='Catálogo de flujos que este cliente tiene activos.',
    )
    output_instagram = fields.Boolean(
        string="Variante corta por plataforma",
        help='Si se genera una variante corta (output_corto) para Instagram/Meta.',
    )
    active = fields.Boolean(default=True)
    brand_name = fields.Char(
        string="Nombre de marca",
        help="Marca que ve el cliente final. Si está vacío se usa el nombre del negocio.",
    )
    attribution_enabled = fields.Boolean(string="Atribución de plataforma")
    attribution_text = fields.Char(
        string="Texto de atribución",
        default="@integraiaconodoo",
    )

    @api.model
    def _get_active_config(self):
        """Retorna la config de negocio activa (la más reciente) o vacío."""
        return self.sudo().search([('active', '=', True)], order='id desc', limit=1)

    @api.model
    def _get_brand_settings(self):
        """(brand_name, attribution_enabled, attribution_text) desde la config
        activa; fallback a ir.config_parameter si no hay config (modo legacy)."""
        config = self._get_active_config()
        if config:
            return (
                config.brand_name,
                config.attribution_enabled,
                config.attribution_text,
            )
        params = self.env['ir.config_parameter'].sudo()
        return (
            params.get_param('ai_chatbot_1_portal.brand_name', ''),
            params.get_param(
                'ai_chatbot_1_portal.platform_promotion_enabled', 'False'
            ) == 'True',
            params.get_param(
                'ai_chatbot_1_portal.platform_promotion_text',
                '@integraiaconodoo',
            ),
        )

    def _notificar(self, titulo, mensaje, tipo='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': titulo,
                'message': mensaje,
                'type': tipo,
                'sticky': True,
            },
        }

    def _leer_datos_rag(self):
        """
        Lee y parsea la tabla n8n_vectors (única fuente de verdad).
        :return: dict con 'ok' bool. Si ok: filas, secciones, role_partes,
            conocimiento, contacto, nombre_cliente, documentos.
        """
        cr = self.env.cr
        try:
            cr.execute("SELECT to_regclass('public.n8n_vectors')")
            if not cr.fetchone()[0]:
                return {
                    'ok': False, 'titulo': 'RAG no disponible',
                    'mensaje': 'La tabla n8n_vectors no existe. Ejecuta primero '
                               'la ingestión RAG en n8n.', 'tipo': 'warning',
                }
            cr.execute("SELECT file_id, text, "
                       "metadata->'loc'->'lines'->>'from' "
                       "FROM n8n_vectors")
            filas = cr.fetchall()
        except Exception:
            _logger.exception('_leer_datos_rag: error leyendo n8n_vectors')
            return {
                'ok': False, 'titulo': 'Error RAG',
                'mensaje': 'No se pudo leer la tabla n8n_vectors.', 'tipo': 'danger',
            }
        if not filas:
            return {
                'ok': False, 'titulo': 'RAG vacío',
                'mensaje': 'La tabla n8n_vectors no tiene datos cargados.',
                'tipo': 'warning',
            }

        def _pos(fila):
            try:
                return int(fila[2])
            except (TypeError, ValueError):
                return 10 ** 6

        filas.sort(key=lambda f: (f[0], _pos(f)))
        secciones = _detectar_secciones([(f[0], f[1]) for f in filas])

        def _dedupe(lista):
            """Elimina secciones duplicadas: conserva la primera versión no vacía
            por nombre normalizado y descarta repeticiones posteriores."""
            vistos = set()
            resultado = []
            for n, t in lista:
                t = (t or '').strip()
                if not t:
                    continue
                clave = _normalizar(n)
                if clave in vistos:
                    continue
                vistos.add(clave)
                resultado.append((n, t))
            return resultado

        secciones = _dedupe(secciones)

        role_partes = [t for (n, t) in secciones if _es_seccion_role(n)]
        conocimiento = [(n, t) for (n, t) in secciones
                        if not _es_seccion_role(n)]
        contacto = next(
            (t for (n, t) in secciones if _normalizar(n) == 'CONTACTO'), None)

        role = "\n\n".join(role_partes) if role_partes else ''
        return {
            'ok': True, 'titulo': 'RAG', 'tipo': 'success',
            'filas': filas, 'secciones': secciones,
            'role_partes': role_partes, 'conocimiento': conocimiento,
            'contacto': contacto,
            'nombre_cliente': self._extraer_nombre_cliente(role),
            'documentos': len(set(f[0] for f in filas)),
        }

    def _extraer_nombre_cliente(self, role_texto):
        """Deriva el nombre del negocio desde el role (patrón 'BOT X')."""
        for linea in (role_texto or '').splitlines():
            m = re.match(r'\s*BOT\s+(.+?)\s*$', linea.strip(), re.IGNORECASE)
            if m:
                valor = re.split(r'[\.\,\n]', m.group(1))[0].strip()
                if valor:
                    return valor
        return 'Cliente RAG'

    def _generar_intenciones_sistema(self, conocimiento):
        """
        Crea las intenciones sistema desde las secciones del RAG. Las secciones
        que coinciden con una intención sistema se usan como respuesta; las que
        faltan (BASE_SISTEMA) quedan como ranuras vacías para el humano.
        :return: (vals, nombres_procesados) para seguir con las de contenido.
        """
        vals = []
        por_seccion = {_normalizar(n): (n, t) for n, t in conocimiento}
        procesadas = set()
        for norm_key, cfg in _SYSTEM_INTENCIONES.items():
            output = ''
            if norm_key in por_seccion:
                output = por_seccion[norm_key][1].strip()[:2000]
                procesadas.add(norm_key)
            elif norm_key not in _BASE_SISTEMA:
                continue
            if not output and cfg.get('output_default'):
                # Intenciones universales (p. ej. manejo de imágenes, FALLBACK)
                # con guion por defecto: no quedan vacías, el humano puede
                # editarlas luego.
                output = cfg['output_default']
            vals.append({
                'config_id': self.id,
                'nombre': cfg['nombre'],
                'keywords': cfg['keywords'],
                'prioridad': cfg['prioridad'],
                'tipo_pregunta': cfg['tipo_pregunta'],
                'es_menu': cfg['es_menu'],
                'output_largo': output,
                'es_auto_rag': True,
            })
        return vals, procesadas

    def _refrescar_desde_rag(self):
        """
        Lee n8n_vectors, actualiza role/contacto/bloque_conocimiento de la
        config y regenera las intenciones es_auto_rag (sistema + contenido).

        :return: dict resumen:
            {'ok': bool, 'titulo': str, 'mensaje': str, 'tipo': str,
             'documentos': int, 'secciones': int, 'intenciones': int,
             'role_actualizado': bool}
        """
        self.ensure_one()
        datos = self._leer_datos_rag()
        if not datos['ok']:
            return {
                'ok': False, 'titulo': datos['titulo'],
                'mensaje': datos['mensaje'], 'tipo': datos['tipo'],
                'documentos': 0, 'secciones': 0, 'intenciones': 0,
                'role_actualizado': False,
            }

        secciones = datos['secciones']
        role_partes = datos['role_partes']
        conocimiento = datos['conocimiento']

        vals_config = {}
        if role_partes:
            vals_config['role'] = "\n\n".join(role_partes)[:12000]
        contenido = [(n, t) for (n, t) in conocimiento
                     if _normalizar(n) != 'CONTACTO']
        if contenido:
            vals_config['bloque_conocimiento'] = (
                "\n\n".join(t for _, t in contenido)[:12000])
        if datos['contacto']:
            vals_config['contacto'] = datos['contacto'][:4000]
        if vals_config:
            self.write(vals_config)

        self.env['chatbot.intencion'].search([
            ('config_id', '=', self.id),
            ('es_auto_rag', '=', True),
        ]).unlink()

        vals_sistema, procesadas = self._generar_intenciones_sistema(conocimiento)

        for v in vals_sistema:
            if v.get('nombre') == 'FALLBACK' and not (v.get('output_largo') or '').strip():
                v['output_largo'] = _SYSTEM_INTENCIONES['FALLBACK']['output_default']

        vals = list(vals_sistema)
        vistos = set()
        indice = 0
        for nombre, texto in conocimiento:
            if _normalizar(nombre) in procesadas:
                continue
            nombre = (nombre or 'SECCION_%d' % (indice + 1)).upper().strip()
            texto = texto.strip()
            if len(texto) < 40:
                continue
            clave = (nombre, texto)
            if clave in vistos:
                continue
            vistos.add(clave)
            vals.append({
                'config_id': self.id,
                'nombre': nombre,
                'keywords': _extract_keywords(texto),
                'prioridad': 60 + indice * 10,
                'tipo_pregunta': nombre,
                'output_largo': texto[:2000],
                'es_auto_rag': True,
            })
            indice += 1
        if vals:
            self.env['chatbot.intencion'].create(vals)

        mensaje = (
            'Documentos: %d · Secciones: %d · Intenciones creadas: %d. '
            'Bloque de conocimiento actualizado.'
            % (datos['documentos'], len(secciones), len(vals)))
        if role_partes:
            mensaje += ' Role actualizado desde el documento.'
        else:
            mensaje += (' No se encontró sección TÚ ERES: '
                        'se conservó el role actual.')
        return {
            'ok': True, 'titulo': 'Refrescar desde RAG', 'mensaje': mensaje,
            'tipo': 'success', 'documentos': datos['documentos'],
            'secciones': len(secciones), 'intenciones': len(vals),
            'role_actualizado': bool(role_partes),
        }

    def action_refrescar_desde_rag(self):
        """Botón: regenera intenciones RAG y base de conocimiento."""
        res = self._refrescar_desde_rag()
        return self._notificar(
            res.get('titulo', 'Refrescar desde RAG'),
            res['mensaje'], res.get('tipo', 'success'))

    @api.model
    def _crear_cliente_desde_rag_por_accion(self):
        """Crea/actualiza el único cliente desde n8n_vectors (server action)."""
        return self.browse().action_crear_cliente_desde_rag()

    def action_crear_cliente_desde_rag(self):
        """
        Crea (o reutiliza) la config del único cliente desde n8n_vectors y
        ejecuta el pipeline completo (intenciones, detección/activación de
        flujos y mappings). Devuelve la acción para abrir la config generada.
        """
        datos = self._leer_datos_rag()
        if not datos['ok']:
            return self._notificar(
                datos['titulo'], datos['mensaje'], datos['tipo'])

        config = self or self._get_active_config()
        if not config:
            config = self.sudo().create({'name': datos['nombre_cliente']})

        res = config.action_recargar_todo_desde_rag()
        if res.get('params', {}).get('type') == 'warning':
            return res

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'chatbot.config',
            'res_id': config.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'ai_chatbot_1_portal.view_chatbot_config_form').id,
            'target': 'current',
        }

    def _detectar_flujos_desde_rag(self, texto, flujos):
        """
        Detecta qué flujos aplican al contenido del cliente (RAG).

        Estrategia híbrida:
        1. Keywords deterministas: palabras_clave de cada flujo contra el texto,
           insensibles a acentos y con bordes de palabra.
        2. Respaldo IA: si ningún flujo matcheó y hay texto, delega en
           gpt.service.detectar_flujos_por_prompt.

        :param texto: texto del conocimiento/role del cliente (normalizará).
        :param flujos: recordset chatbot.flujo (catálogo completo).
        :return: dict {'flujos': recordset, 'metodo': 'keywords'|'ia'|'ninguno'}
        """
        texto_norm = _normalizar(texto or '')
        candidatos = []
        matched = []
        for flujo in flujos:
            keywords = [k.strip() for k in (flujo.palabras_clave or '').split(',')]
            keywords = [_normalizar(k) for k in keywords if k]
            if not keywords:
                continue
            candidatos.append(flujo)
            pattern = '|'.join(r'\b' + re.escape(k) + r'\b' for k in keywords)
            if texto_norm and re.search(pattern, texto_norm):
                matched.append(flujo)

        metodo = 'keywords' if matched else 'ninguno'

        if not matched and texto and texto.strip():
            flujos_info = [
                {'name': f.name,
                 'descripcion_intencion': f.descripcion_intencion or '',
                 'palabras_clave': f.palabras_clave or ''}
                for f in candidatos
            ]
            if flujos_info:
                try:
                    gpt_service = self.env.get('gpt.service')
                    if gpt_service:
                        recomendados = gpt_service.sudo().detectar_flujos_por_prompt(
                            texto, flujos_info)
                        matched = list(flujos.filtered(
                            lambda f: f.name in (recomendados or [])))
                        if matched:
                            metodo = 'ia'
                except Exception as e:
                    _logger.warning(
                        '_detectar_flujos_desde_rag: falló la IA de respaldo (%s).',
                        e)
        flujos_matched = self.env['chatbot.flujo'].browse(
            [f.id for f in matched])
        # El flujo de imágenes/archivos es universal: siempre disponible para
        # todo cliente (puede enviar fotos, logos o comprobantes por WhatsApp).
        flujo_imagenes = flujos.filtered(
            lambda f: f.name == 'flujo_resultados_imagenes')
        flujos_matched = (flujos_matched | flujo_imagenes)
        return {'flujos': flujos_matched, 'metodo': metodo}

    def _vincular_flow_id_en_intenciones(self, flujos):
        """
        Vincula 'flow_id' (Flujo que dispara) en las intenciones es_auto_rag
        cuyo texto/palabras clave coincidan con un flujo detectado.
        No toca intenciones manuales.
        :return: cantidad de intenciones vinculadas.
        """
        vinculadas = 0
        for intencion in self.intencion_ids.filtered(lambda i: i.es_auto_rag):
            texto_i = _normalizar(' '.join(filter(None, [
                intencion.nombre or '',
                intencion.keywords or '',
                intencion.output_largo or '',
            ])))
            mejor = self.env['chatbot.flujo']
            mejor_score = 0
            for f in flujos:
                keywords = [k.strip() for k in (f.palabras_clave or '').split(',')]
                keywords = [_normalizar(k) for k in keywords if k]
                if not keywords:
                    continue
                score = 0
                for k in keywords:
                    if re.search(r'\b' + re.escape(k) + r'\b', texto_i):
                        score += 1
                if score > mejor_score:
                    mejor = f
                    mejor_score = score
            if mejor and intencion.flow_id.id != mejor.id:
                intencion.flow_id = mejor.id
                vinculadas += 1
        return vinculadas

    def action_recargar_todo_desde_rag(self):
        """
        Botón único: recarga intenciones desde n8n_vectors, detecta
        inteligentemente los flujos del cliente, activa flujos + pasos y
        (re)genera los Chatwoot Mappings para que el bot ofrezca los flujos
        al cliente cuando pregunte por chat.
        """
        self.ensure_one()

        resumen_rag = self._refrescar_desde_rag()
        if not resumen_rag['ok']:
            return self._notificar(
                resumen_rag.get('titulo', 'Recargar desde RAG'),
                resumen_rag['mensaje'], resumen_rag.get('tipo', 'warning'))

        # Auto-curación del catálogo: si borraron los flujos base, se recrean
        # (archivados) para que la detección tenga candidatos.
        flujo_model = self.env['chatbot.flujo'].sudo()
        flujo_model._ensure_catalogo_flujos()
        flujos = flujo_model.with_context(active_test=False).search([])

        texto = "\n\n".join(filter(None, [
            self.role or '', self.contacto or '', self.bloque_conocimiento or '']))
        deteccion = self._detectar_flujos_desde_rag(texto, flujos)
        flujos_detectados = deteccion['flujos']
        metodo = deteccion['metodo']

        if not flujos_detectados:
            return self._notificar(
                'Recargar desde RAG',
                f"Intenciones RAG regeneradas ({resumen_rag['intenciones']}), "
                'pero no se detectaron flujos aplicables '
                '(sin keywords y sin recomendación IA). Se conservó el estado '
                'actual de los flujos.',
                'warning')

        self.write({'flujo_ids': [(6, 0, flujos_detectados.ids)]})
        vinculadas = self._vincular_flow_id_en_intenciones(flujos_detectados)

        resultado = flujo_model._aplicar_deteccion_desde_config(self)
        activados = resultado.get('activados', [])
        archivados = resultado.get('archivados', [])

        mappings_activos = 0
        mappings_rellenados = 0
        try:
            mapping_model = self.env['chatwoot.mapping']
            flujos_activos = flujo_model.search([('active', '=', True)])
            mappings = mapping_model.sudo().search(
                [('flow_id', 'in', flujos_activos.ids)])
            mappings_activos = len(mappings)
            mappings_rellenados = mapping_model.sudo()._rellenar_defaults_vacios(
                mappings)
        except KeyError:
            _logger.warning(
                'action_recargar_todo_desde_rag: odoo_chatwoot_connector no '
                'instalado; se omitió la gestión de mappings.')
        except Exception:
            _logger.exception(
                'action_recargar_todo_desde_rag: falló la gestión de mappings.')

        mensaje = (
            f"RAG: {resumen_rag['documentos']} documento(s), "
            f"{resumen_rag['secciones']} sección(es), "
            f"{resumen_rag['intenciones']} intención(es).\n"
            f"Detección: {metodo}. Vinculadas a flujo: {vinculadas}.\n"
            f"Flujos activados: {', '.join(activados) or 'ninguno'}."
        )
        if archivados:
            mensaje += f"\nFlujos archivados: {', '.join(archivados)}"
        if mappings_activos:
            mensaje += (
                f"\nMappings para flujos activos: {mappings_activos} "
                f"({mappings_rellenados} rellenado(s) con el agente por defecto)."
            )
        return self._notificar('Recargar desde RAG', mensaje, 'success')

    def action_activar_flujos(self):
        """Activa los flujos de esta config (+ default) y archiva el resto."""
        self.ensure_one()
        resultado = self.env['chatbot.flujo'].sudo()._aplicar_deteccion_desde_config(
            self)
        activados = resultado.get('activados', [])
        archivados = resultado.get('archivados', [])
        mensaje = resultado.get('mensaje', '')
        if activados:
            mensaje += f"\nActivados: {', '.join(activados)}"
        if archivados:
            mensaje += f"\nArchivados: {', '.join(archivados)}"
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Activar flujos'),
                'message': mensaje or 'Sin cambios.',
                'type': 'success',
                'sticky': True,
            },
        }