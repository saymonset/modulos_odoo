import re
import unicodedata

from odoo import api, fields, models, _

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
        string="Flujos activos",
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

    def action_refrescar_desde_rag(self):
        self.ensure_one()
        cr = self.env.cr
        try:
            cr.execute("SELECT to_regclass('public.n8n_vectors')")
            existe = cr.fetchone()[0]
            if not existe:
                return self._notificar(
                    'RAG no disponible',
                    'La tabla n8n_vectors no existe. Ejecuta primero la '
                    'ingestión RAG en n8n.',
                    'warning')
            cr.execute("SELECT file_id, text, "
                       "metadata->'loc'->'lines'->>'from' "
                       "FROM n8n_vectors")
            filas = cr.fetchall()
        except Exception:
            return self._notificar(
                'Error RAG', 'No se pudo leer la tabla n8n_vectors.', 'danger')
        if not filas:
            return self._notificar(
                'RAG vacío',
                'La tabla n8n_vectors no tiene datos cargados.', 'warning')

        def _pos(fila):
            try:
                return int(fila[2])
            except (TypeError, ValueError):
                return 10 ** 6

        filas.sort(key=lambda f: (f[0], _pos(f)))
        secciones = _detectar_secciones([(f[0], f[1]) for f in filas])

        role_partes = [t for (n, t) in secciones if _es_seccion_role(n)]
        conocimiento = [(n, t) for (n, t) in secciones
                        if not _es_seccion_role(n)]

        vals_config = {}
        if role_partes:
            vals_config['role'] = "\n\n".join(role_partes)[:12000]
        if conocimiento:
            vals_config['bloque_conocimiento'] = (
                "\n\n".join(t for _, t in conocimiento)[:12000])
        contacto = next(
            (t for (n, t) in secciones if _normalizar(n) == 'CONTACTO'), None)
        if contacto:
            vals_config['contacto'] = contacto[:4000]
        if vals_config:
            self.write(vals_config)

        self.env['chatbot.intencion'].search([
            ('config_id', '=', self.id),
            ('es_auto_rag', '=', True),
        ]).unlink()

        vals = []
        vistos = set()
        for i, (nombre, texto) in enumerate(conocimiento):
            nombre = (nombre or 'SECCION_%d' % (i + 1)).upper().strip()
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
                'prioridad': 60 + i * 10,
                'tipo_pregunta': nombre,
                'output_largo': texto[:2000],
                'es_auto_rag': True,
            })
        if vals:
            self.env['chatbot.intencion'].create(vals)

        mensaje = (
            'Documentos: %d · Secciones: %d · Intenciones creadas: %d. '
            'Bloque de conocimiento actualizado.'
            % (len(set(f[0] for f in filas)), len(secciones), len(vals)))
        if role_partes:
            mensaje += ' Role actualizado desde el documento.'
        else:
            mensaje += (' No se encontró sección TÚ ERES: '
                        'se conservó el role actual.')
        return self._notificar('Refrescar desde RAG', mensaje, 'success')

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