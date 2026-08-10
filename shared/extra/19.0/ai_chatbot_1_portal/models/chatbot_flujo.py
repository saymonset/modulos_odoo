import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

_CHAR_ACCENT_MAP = {
    'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
    'ü': 'u', 'ñ': 'n', 'Á': 'a', 'É': 'e', 'Í': 'i',
    'Ó': 'o', 'Ú': 'u', 'Ü': 'u', 'Ñ': 'n',
}


def _normalizar_texto(texto):
    """Minúsculas y sin acentos para búsqueda robusta de keywords."""
    if not texto:
        return ''
    texto = texto.lower()
    return ''.join(_CHAR_ACCENT_MAP.get(c, c) for c in texto)


class ChatbotFlujo(models.Model):
    _name = "chatbot.flujo"
    _description = "Flujo de chatbot"

    name = fields.Char(string="Nombre del flujo", required=True)
    company_id = fields.Many2one("res.company", string="Empresa", required=True)
    paso_ids = fields.One2many(
        "chatbot.paso",
        "flujo_id",
        string="Pasos",
        copy=True,
    )
    active = fields.Boolean(default=True)

    grupo_asignado = fields.Selection(
        selection=[
            ("Grupo Citas", "Grupo Citas"),
            ("Grupo Ventas", "Grupo Ventas"),
            ("Grupo Laboratorio", "Grupo Laboratorio"),
            ("Grupo Imagenología", "Grupo Imagenología"),
            ("Grupo Informativo", "Grupo Informativo"),
        ],
        string="Grupo CRM",
        help="Grupo de ventas/CRM que gestiona los leads de este flujo. "
             "Se autocompleta según el nombre del flujo.",
    )

    team_id = fields.Many2one(
        'crm.team',
        string='Equipo CRM',
        ondelete='set null',
        help='Enlace directo al equipo/grupo CRM responsable de este flujo',
    )

    routing_key = fields.Char(
        string='Código de enrutamiento',
        help='Identificador que n8n envía como equipo_asignado cuando el agente '
             'activa este flujo. Si se deja vacío, se usa el nombre del flujo.',
    )

    descripcion_intencion = fields.Text(
        string='Descripción para el agente',
        help='Instrucción que se inyecta al prompt del agente para explicarle '
             'cuándo debe activar este flujo.',
    )

    condiciones_no_inicio = fields.Text(
        string='Condiciones para NO iniciar',
        help='Explica al agente en qué casos no debe activar este flujo '
             '(por ejemplo: solo consultas informativas).',
    )

    politica_inicio = fields.Selection([
        ('immediate', 'Inmediata (al detectar la intención)'),
        ('confirmation', 'Requiere confirmación del usuario'),
        ('manual', 'Solo por botón o comando'),
    ], string='Política de inicio', default='immediate')

    palabras_clave = fields.Text(
        string='Palabras clave para auto-detección',
        help='Lista separada por coma. El detector automático busca estas '
             'palabras en el system_prompt del cliente para decidir si este '
             'flujo aplica a su negocio. Ej: clinica,hospital,salud,doctor',
    )

    generar_pasos_automatico = fields.Boolean(
        string='Generar pasos automáticamente',
        default=True,
        help='Al crear el flujo, genera la plantilla de pasos genéricos. '
             'Desactívalo para crear los pasos manualmente según el cliente.',
    )

    # ============================================================
    # MÉTODOS BASE PARA OBTENER LOS PASOS OBLIGATORIOS
    # ============================================================
    
    def _get_pasos_obligatorios(self):
        """
        Retorna la lista de pasos OBLIGATORIOS que deben tener TODOS los flujos.
        Estos son: phone, name, vat, birthdate, consentimiento
        """
        return [
            {
                "secuencia": 10,
                "nombre_interno": "solicitar_phone",
                "nombre_mostrar": "Teléfono",
                "tipo_dato": "text",
                "campo_destino": "phone",
                "es_requerido": True,
                "es_paso_telefono": True,
                "mensaje_prompt": "Por favor, ingresa tu número de teléfono:",
                "mensaje_error": "Número inválido, intenta de nuevo.",
            },
            {
                "secuencia": 11,
                "nombre_interno": "solicitar_name",
                "nombre_mostrar": "Nombre completo",
                "tipo_dato": "text",
                "campo_destino": "name",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, ingresa tu nombre completo:",
                "mensaje_error": "Nombre inválido, intenta de nuevo.",
            },
            {
                "secuencia": 12,
                "nombre_interno": "solicitar_vat",
                "nombre_mostrar": "Cédula",
                "tipo_dato": "text",
                "campo_destino": "vat",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, ingresa tu número de cédula:",
                "mensaje_error": "Cédula inválida, intenta de nuevo.",
            },
            {
                "secuencia": 13,
                "nombre_interno": "solicitar_birthdate",
                "nombre_mostrar": "Fecha de nacimiento",
                "tipo_dato": "date",
                "campo_destino": "birthdate",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, ingresa tu fecha de nacimiento (DD/MM/YYYY):",
                "mensaje_error": "Fecha inválida, intenta de nuevo con formato DD/MM/YYYY.",
            },
            {
                "secuencia": 22,
                "nombre_interno": "solicitar_consentimiento",
                "nombre_mostrar": "Consentimiento WhatsApp",
                "tipo_dato": "boolean",
                "campo_destino": "consentimiento_whatsapp",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Aceptas que te enviemos mensajes informativos y recordatorios por WhatsApp? Responde sí o no.",
                "mensaje_error": "Por favor responde 'sí' o 'no'.",
            },
        ]
    
    def _get_pasos_opcionales(self):
        """
        Retorna la lista de pasos OPCIONALES para flujos genéricos.
        """
        return [
            {
                "secuencia": 14,
                "nombre_interno": "solicitar_servicio",
                "nombre_mostrar": "Servicio solicitado",
                "tipo_dato": "text",
                "campo_destino": "servicio_solicitado",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Qué servicio deseas?",
                "mensaje_error": "",
            },
            {
                "secuencia": 15,
                "nombre_interno": "solicitar_fecha_preferida",
                "nombre_mostrar": "Fecha preferida",
                "tipo_dato": "text",
                "campo_destino": "fecha_preferida",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": 'Indica una fecha preferida (DD/MM/YYYY) o escribe "lo antes posible"',
                "mensaje_error": "Formato de fecha inválido. Usa DD/MM/YYYY.",
            },
            {
                "secuencia": 16,
                "nombre_interno": "solicitar_hora_preferida",
                "nombre_mostrar": "Horario preferido",
                "tipo_dato": "text",
                "campo_destino": "hora_preferida",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Qué horario prefieres? (mañana, tarde, cualquier hora)",
                "mensaje_error": "",
            },
            {
                "secuencia": 17,
                "nombre_interno": "solicitar_medio_pago",
                "nombre_mostrar": "Medio de pago",
                "tipo_dato": "text",
                "campo_destino": "medio_pago",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Cómo piensas pagar? (efectivo, tarjeta, etc.)",
                "mensaje_error": "",
            },
            {
                "secuencia": 18,
                "nombre_interno": "solicitar_es_paciente_nuevo",
                "nombre_mostrar": "¿Eres cliente nuevo?",
                "tipo_dato": "text",
                "campo_destino": "es_paciente_nuevo",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Es tu primera consulta? Responde sí o no",
                "mensaje_error": "Responde sí o no.",
            },
            {
                "secuencia": 19,
                "nombre_interno": "solicitar_membresia_interes",
                "nombre_mostrar": "¿Interés en membresía?",
                "tipo_dato": "boolean",
                "campo_destino": "membresia_interes",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Te interesa recibir información sobre nuestros planes? (sí/no)",
                "mensaje_error": "Responde sí o no.",
            },
            {
                "secuencia": 20,
                "nombre_interno": "solicitar_foto_vat",
                "nombre_mostrar": "Foto de cédula",
                "tipo_dato": "image",
                "campo_destino": "foto_vat",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Comparte la foto de tu cédula",
                "mensaje_error": "",
            },
            {
                "secuencia": 21,
                "nombre_interno": "solicitar_imagenes_adicionales",
                "nombre_mostrar": "Imágenes adicionales",
                "tipo_dato": "image",
                "campo_destino": "imagenes_adicionales",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Comparte imágenes adicionales si lo deseas",
                "mensaje_error": "",
            },
            {
                "secuencia": 23,
                "nombre_interno": "solicitar_email",
                "nombre_mostrar": "Correo electrónico",
                "tipo_dato": "text",
                "campo_destino": "email",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Opcional: ingresa tu correo electrónico para recibir información adicional. Si no deseas proporcionarlo, escribe 'omitir'.",
                "mensaje_error": "El correo no parece válido. Intenta de nuevo o escribe 'omitir' para saltar este paso.",
            },
        ]
    
    # ============================================================
    # PASOS PERSONALIZADOS PARA CADA TIPO DE FLUJO
    # ============================================================
    
    def _get_pasos_para_medios_propios(self):
        """
        Pasos específicos para el flujo flujo_citas_medios_propios
        """
        pasos = self._get_pasos_obligatorios()
        pasos.extend([
            {
                "secuencia": 20,
                "nombre_interno": "solicitar_foto_vat",
                "nombre_mostrar": "Foto de cédula o pasaporte",
                "tipo_dato": "image",
                "campo_destino": "foto_vat",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, envíe una imagen o foto de su cédula o pasaporte.\nSus datos están protegidos bajo nuestra política de privacidad.\nAsegúrese de que la imagen sea clara.",
                "mensaje_error": "Por favor envía una imagen clara de tu cédula o pasaporte.",
            },
            {
                "secuencia": 14,
                "nombre_interno": "solicitar_consulta_deseada",
                "nombre_mostrar": "Consulta o estudio deseado",
                "tipo_dato": "text",
                "campo_destino": "consulta_deseada",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Indique la consulta o estudio que desea realizar.\n\nPuede describir brevemente el servicio que necesita.",
                "mensaje_error": "Por favor indica qué consulta o estudio deseas.",
            },
        ])
        return pasos
    
    def _get_pasos_para_seguro(self):
        """
        Pasos específicos para el flujo flujo_citas_seguro
        """
        brand = self.env['ir.config_parameter'].sudo().get_param(
            'ai_chatbot_1_portal.brand_name') or 'IntegraIA'
        pasos = self._get_pasos_obligatorios()
        pasos.extend([
            {
                "secuencia": 12.5,
                "nombre_interno": "solicitar_nombre_seguro",
                "nombre_mostrar": "Nombre del seguro médico",
                "tipo_dato": "text",
                "campo_destino": "nombre_seguro",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": f"Has indicado que usarás un seguro.\nPor favor, escribe el nombre completo de tu seguro para validar la cobertura y continuar con tu solicitud.\n\nEjemplos:\n    • FASME\n    • FASDEM\n    • SENIAT\n    • ALCALDIA DE MANEIRO\n    • LA INTERNACIONAL\n\nSi tu seguro no está en convenio con {brand}, nuestro equipo te informará las opciones de pago particular.",
                "mensaje_error": "Por favor indica el nombre de tu seguro.",
            },
            {
                "secuencia": 20,
                "nombre_interno": "solicitar_foto_vat",
                "nombre_mostrar": "Foto de cédula o pasaporte",
                "tipo_dato": "image",
                "campo_destino": "foto_vat",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, envíe una imagen o foto de su cédula o pasaporte.\nSus datos están protegidos bajo nuestra política de privacidad.\nAsegúrese de que la imagen sea clara.",
                "mensaje_error": "Por favor envía una imagen clara de tu cédula o pasaporte.",
            },
            {
                "secuencia": 14,
                "nombre_interno": "solicitar_consulta_deseada",
                "nombre_mostrar": "Consulta o estudio deseado",
                "tipo_dato": "text",
                "campo_destino": "consulta_deseada",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Indique la consulta o estudio que desea realizar.\n\nPuede describir brevemente el servicio que necesita.",
                "mensaje_error": "Por favor indica qué consulta o estudio deseas.",
            },
        ])
        return pasos
    
    def _get_pasos_para_resultados_lab(self):
        """
        Pasos específicos para flujo_resultados_laboratorio
        """
        return [
            {
                "secuencia": 5,
                "nombre_interno": "solicitar_phone",
                "nombre_mostrar": "Teléfono",
                "tipo_dato": "text",
                "campo_destino": "phone",
                "es_requerido": True,
                "es_paso_telefono": True,
                "mensaje_prompt": "Por favor, ingresa tu número de teléfono:",
                "mensaje_error": "Número inválido, intenta de nuevo.",
            },
            {
                "secuencia": 6,
                "nombre_interno": "solicitar_name",
                "nombre_mostrar": "Nombre completo",
                "tipo_dato": "text",
                "campo_destino": "name",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, ingresa tu nombre completo:",
                "mensaje_error": "Nombre inválido, intenta de nuevo.",
            },
            {
                "secuencia": 10,
                "nombre_interno": "solicitar_identificacion",
                "nombre_mostrar": "Identificación del cliente",
                "tipo_dato": "text",
                "campo_destino": "identificacion_paciente",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, escribe el nombre completo y cédula del cliente:",
                "mensaje_error": "Por favor proporciona nombre completo y cédula.",
            },
            {
                "secuencia": 11,
                "nombre_interno": "solicitar_estudio",
                "nombre_mostrar": "Estudio solicitado",
                "tipo_dato": "text",
                "campo_destino": "estudio_solicitado",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Qué estudio de laboratorio necesitas? Indica el nombre del estudio.",
                "mensaje_error": "Por favor indica qué estudio necesitas.",
            },
            {
                "secuencia": 22,
                "nombre_interno": "solicitar_consentimiento",
                "nombre_mostrar": "Consentimiento WhatsApp",
                "tipo_dato": "boolean",
                "campo_destino": "consentimiento_whatsapp",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Aceptas que te enviemos mensajes informativos y recordatorios por WhatsApp? Responde sí o no.",
                "mensaje_error": "Por favor responde 'sí' o 'no'.",
            },
        ]
    
    def _get_pasos_para_resultados_imagenes(self):
        """
        Pasos específicos para flujo_resultados_imagenes
        """
        return [
            {
                "secuencia": 5,
                "nombre_interno": "solicitar_phone",
                "nombre_mostrar": "Teléfono",
                "tipo_dato": "text",
                "campo_destino": "phone",
                "es_requerido": True,
                "es_paso_telefono": True,
                "mensaje_prompt": "Por favor, ingresa tu número de teléfono:",
                "mensaje_error": "Número inválido, intenta de nuevo.",
            },
            {
                "secuencia": 6,
                "nombre_interno": "solicitar_name",
                "nombre_mostrar": "Nombre completo",
                "tipo_dato": "text",
                "campo_destino": "name",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, ingresa tu nombre completo:",
                "mensaje_error": "Nombre inválido, intenta de nuevo.",
            },
            {
                "secuencia": 10,
                "nombre_interno": "solicitar_identificacion",
                "nombre_mostrar": "Identificación del cliente",
                "tipo_dato": "text",
                "campo_destino": "identificacion_paciente",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "Por favor, escribe el nombre completo y cédula del cliente:",
                "mensaje_error": "Por favor proporciona nombre completo y cédula.",
            },
            {
                "secuencia": 11,
                "nombre_interno": "solicitar_estudio",
                "nombre_mostrar": "Estudio solicitado",
                "tipo_dato": "text",
                "campo_destino": "estudio_solicitado",
                "es_requerido": False,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Qué estudio de imágenes necesitas? Indica el nombre del estudio.",
                "mensaje_error": "Por favor indica qué estudio necesitas.",
            },
            {
                "secuencia": 22,
                "nombre_interno": "solicitar_consentimiento",
                "nombre_mostrar": "Consentimiento WhatsApp",
                "tipo_dato": "boolean",
                "campo_destino": "consentimiento_whatsapp",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "¿Aceptas que te enviemos mensajes informativos y recordatorios por WhatsApp? Responde sí o no.",
                "mensaje_error": "Por favor responde 'sí' o 'no'.",
            },
        ]
    
    def _get_todos_los_pasos(self):
        """Retorna TODOS los pasos (obligatorios + opcionales) para flujos genéricos"""
        return self._get_pasos_obligatorios() + self._get_pasos_opcionales()
    
    # ============================================================
    # MÉTODOS PARA CREAR PASOS EN UN FLUJO (VERSIÓN PERSONALIZADA)
    # ============================================================
    
    def _get_pasos_data_para_flujo(self):
        """
        Retorna la plantilla de pasos según el nombre del flujo (coincide con n8n).
        """
        if self.name == "flujo_citas_medios_propios":
            return self._get_pasos_para_medios_propios()
        elif self.name == "flujo_citas_seguro":
            return self._get_pasos_para_seguro()
        elif self.name == "flujo_resultados_laboratorio":
            return self._get_pasos_para_resultados_lab()
        elif self.name == "flujo_resultados_imagenes":
            return self._get_pasos_para_resultados_imagenes()
        elif self.name == "flujo_agendamiento_precios":
            # Flujo informativo: mostrar información de precios primero.
            # No solicitamos teléfono como primer paso; el usuario puede
            # confirmar que desea agendar y entonces iniciar el flujo de agendamiento.
            return [
                {
                    "secuencia": 1,
                    "nombre_interno": "informar_precios",
                    "nombre_mostrar": "Información de precios",
                    "tipo_dato": "text",
                    "campo_destino": "informacion_precios",
                    "es_requerido": False,
                    "es_paso_telefono": False,
                    "mensaje_prompt": "Conoce nuestros planes. ¿Deseas que te enviemos una cotización? Responde 'Sí' para continuar.",
                    "mensaje_error": "",
                }
            ]
        return self._get_todos_los_pasos()

    def _crear_pasos_para_flujo(self, incluir_opcionales=True):
        """
        Crea los pasos para este flujo.
        Según el nombre del flujo, usa pasos diferentes.
        """
        Paso = self.env["chatbot.paso"]
        pasos_data = self._get_pasos_data_para_flujo()
        if not incluir_opcionales and self.name not in (
                "flujo_citas_medios_propios",
                "flujo_citas_seguro",
                "flujo_resultados_laboratorio",
                "flujo_resultados_imagenes",
                "flujo_agendamiento_precios"):
            pasos_data = self._get_pasos_obligatorios()
        for paso_data in pasos_data:
            paso_vals = paso_data.copy()
            paso_vals["flujo_id"] = self.id
            Paso.create(paso_vals)
        return True

    def action_regenerar_pasos(self):
        """
        Reconstruye los pasos faltantes de cada flujo desde su plantilla.
        No duplica los existentes (match por nombre_interno), no borra y no
        sobrescribe ningún paso (preserva personalizaciones del usuario).
        """
        Paso = self.env["chatbot.paso"]
        total = 0
        flujos_tocados = 0
        for flujo in self:
            existentes = set(flujo.paso_ids.mapped('nombre_interno'))
            pasos_data = flujo._get_pasos_data_para_flujo()
            creados = 0
            for paso_data in pasos_data:
                if paso_data['nombre_interno'] in existentes:
                    continue
                paso_vals = paso_data.copy()
                paso_vals['flujo_id'] = flujo.id
                Paso.create(paso_vals)
                creados += 1
            if creados:
                total += creados
                flujos_tocados += 1
        mensaje = (
            f"{total} paso(s) recreado(s) en {flujos_tocados} flujo(s)."
            if flujos_tocados
            else "Todos los pasos ya existían: no hubo cambios."
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Regenerar pasos',
                'message': mensaje,
                'type': 'success',
                'sticky': False,
            },
        }
    
    # ============================================================
    # MAPEO CENTRALIZADO: equipo_asignado → Grupo CRM
    # ============================================================

    @api.model
    def _get_mapeo_equipo_grupo(self):
        """
        Fuente de verdad única.
        Retorna un dict {clave: nombre_grupo} donde 'clave' puede ser
        tanto el valor corto de equipo_asignado (ej: CITAS_MP) como
        el name_flow (ej: flujo_citas_medios_propios).
        None = flujo sin agente (informativo).
        """
        return {
            "Agendamiento_Directo": "Grupo Informativo",
            "flujo_agendamiento_directo": "Grupo Informativo",
            "Agendamiento_Precios": "Grupo Informativo",
            "flujo_agendamiento_precios": "Grupo Informativo",
            # Cambiado: flujo_agendamiento_servicios ahora apunta a Grupo Ventas
            "Agendamiento_Servicios": "Grupo Ventas",
            "flujo_agendamiento_servicios": "Grupo Ventas",
            "Agendamiento_Otra_Consulta": "Grupo Citas",
            "flujo_agendamiento_otra_consulta": "Grupo Citas",
            "Agendamiento_Tarjeta": "Grupo Ventas",
            "flujo_ventas": "Grupo Ventas",
            "Ventas": "Grupo Ventas",
            # Aliases de compatibilidad (nombres antiguos)
            "flujo_ventas_unisa": "Grupo Ventas",
            "Ventas_UNISA": "Grupo Ventas",
            "CITAS_MP": "Grupo Citas",
            "flujo_citas_medios_propios": "Grupo Citas",
            "CITAS_SEGUROS": "Grupo Citas",
            "flujo_citas_seguro": "Grupo Citas",
            "RESULTADOS_LAB": "Grupo Laboratorio",
            "flujo_resultados_laboratorio": "Grupo Laboratorio",
            "RESULTADOS_IMAGENES": "Grupo Imagenología",
            "flujo_resultados_imagenes": "Grupo Imagenología",
            "flujo_agendamiento_default": "Grupo Informativo",
        }

    @api.model
    def _get_mapeo_nombre_grupo(self):
        """
        Subconjunto de _get_mapeo_equipo_grupo() con solo las claves
        name_flow (prefijo 'flujo_'). Útil para autocompletar
        grupo_asignado desde el nombre del flujo.
        """
        mapeo = self._get_mapeo_equipo_grupo()
        return {k: v for k, v in mapeo.items() if k.startswith("flujo_")}

    # ============================================================
    # MAPEO CENTRALIZADO: equipo_asignado → texto descriptivo
    # ============================================================

    @api.model
    def _get_mapeo_equipo_descripcion(self):
        """
        Fuente de verdad única.
        Retorna un dict {clave: texto} que describe en español
        el área responsable para cada equipo_asignado.
        """
        return {
            "Agendamiento_Directo": "soporte general e información",
            "flujo_agendamiento_directo": "soporte general e información",
            "Agendamiento_Precios": "información de tienda virtual y planes",
            "flujo_agendamiento_precios": "información de tienda virtual y planes",
            # Cambiado: flujo_agendamiento_servicios ahora apunta a Grupo Ventas
            "Agendamiento_Servicios": "información sobre agentes de IA",
            "flujo_agendamiento_servicios": "información sobre agentes de IA",
            "Agendamiento_Otra_Consulta": "desarrollo y consultoría",
            "flujo_agendamiento_otra_consulta": "desarrollo y consultoría",
            "Agendamiento_Tarjeta": "ventas de hosting y dominio",
            "flujo_ventas": "ventas de hosting y dominio",
            "Ventas": "ventas de hosting y dominio",
            "flujo_ventas_unisa": "ventas de hosting y dominio",
            "Ventas_UNISA": "ventas de hosting y dominio",
            "CITAS_MP": "citas por medios propios",
            "flujo_citas_medios_propios": "citas por medios propios",
            "CITAS_SEGUROS": "citas con seguro médico",
            "flujo_citas_seguro": "citas con seguro médico",
            "RESULTADOS_LAB": "resultados de laboratorio",
            "flujo_resultados_laboratorio": "resultados de laboratorio",
            "RESULTADOS_IMAGENES": "resultados de imagenología",
            "flujo_resultados_imagenes": "resultados de imagenología",
        }

    # ============================================================
    # MÉTODOS PRINCIPALES: CREATE, COPY
    # ============================================================
    
    def write(self, vals):
        """
        Cascade del estado 'active' del flujo hacia sus Chatwoot Mappings.
        Al archivar/desarchivar un flujo, se archiva/desarchiva el mapping
        vinculado (flow_id) para que solo se asignen agentes a flujos activos.
        """
        res = super().write(vals)
        if 'active' in vals:
            try:
                mapping_model = self.env['chatwoot.mapping']
                mappings = mapping_model.sudo().search([('flow_id', 'in', self.ids)])
                if mappings:
                    mappings.write({'active': vals['active']})
                    _logger.info(
                        'cascade: flujos=%s active=%s -> mappings archivados/activados=%s',
                        self.ids, vals['active'], mappings.ids)
            except KeyError:
                _logger.warning(
                    'cascade: modelo chatwoot.mapping no disponible en registry '
                    '(flujo=%s). El mapping NO se sincronizó.', self.ids)
        return res

    _MAPEO_CHATWOOT_POR_FLUJO = {
        'flujo_agendamiento_directo': ('Agendamiento Directo', 'Agendamiento_Directo'),
        'flujo_agendamiento_precios': ('Agendamiento Precios', 'Agendamiento_Precios'),
        'flujo_agendamiento_servicios': ('Agendamiento Servicios', 'Agendamiento_Servicios'),
        'flujo_ventas': ('Ventas', 'Ventas'),
        'flujo_agendamiento_otra_consulta': ('Agendamiento Otra Consulta', 'Agendamiento_Otra_Consulta'),
        'flujo_agendamiento_default': ('Agendamiento Default', ''),
        'flujo_citas_medios_propios': ('Citas Medios Propios', 'CITAS_MP'),
        'flujo_citas_seguro': ('Citas Seguros', 'CITAS_SEGUROS'),
        'flujo_resultados_laboratorio': ('Resultados Laboratorio', 'RESULTADOS_LAB'),
        'flujo_resultados_imagenes': ('Resultados Imágenes', 'RESULTADOS_IMAGENES'),
    }

    def _sincronizar_mappings(self, flujos, activo):
        """Cascade explícito flujo -> chatwoot.mapping (independiente de write)."""
        try:
            mapping_model = self.env['chatwoot.mapping']
        except KeyError:
            _logger.warning('_sincronizar_mappings: chatwoot.mapping no disponible.')
            return
        mappings = mapping_model.sudo().search([('flow_id', 'in', flujos.ids)])
        if mappings:
            mappings.write({'active': activo})
            _logger.info(
                '_sincronizar_mappings: flujos=%s activo=%s -> mappings=%s',
                flujos.ids, activo, mappings.ids)

    def _ensure_mappings_for_flujos(self, flujos):
        """
        Crea un Chatwoot Mapping para cada flujo activo que aún no lo tenga.

        Usa los defaults del conector Chatwoot (agent_id, agent_email, inbox_id)
        configurados en Settings si están seteados; de lo contrario los deja
        vacíos para que un humano los complete en la vista de Mappings.
        """
        try:
            mapping_model = self.env['chatwoot.mapping']
        except KeyError:
            _logger.warning('_ensure_mappings_for_flujos: chatwoot.mapping no disponible.')
            return
        params = self.env['ir.config_parameter'].sudo()
        default_agent_id = params.get_param('chatwoot.default_agent_id', '') or ''
        default_agent_email = params.get_param('chatwoot.default_agent_email', '') or ''
        default_inbox_id = params.get_param('chatwoot.default_inbox_id', '') or ''
        for flujo in flujos:
            existentes = mapping_model.sudo().search([('flow_id', '=', flujo.id)])
            if existentes:
                continue
            label, equipo = self._MAPEO_CHATWOOT_POR_FLUJO.get(
                flujo.name, (flujo.name, ''))
            vals = {
                'name': label,
                'flow_id': flujo.id,
                'equipo_asignado': equipo or False,
                'routing_key': flujo.name or '',
                'active': True,
            }
            if default_agent_id:
                try:
                    vals['chatwoot_agent_id'] = int(default_agent_id)
                except (TypeError, ValueError):
                    _logger.warning('_ensure_mappings_for_flujos: default agent_id inválido=%s', default_agent_id)
            if default_agent_email:
                vals['chatwoot_agent_email'] = default_agent_email
            if default_inbox_id:
                try:
                    vals['chatwoot_inbox_id'] = int(default_inbox_id)
                except (TypeError, ValueError):
                    _logger.warning('_ensure_mappings_for_flujos: default inbox_id inválido=%s', default_inbox_id)
            mapping_model.sudo().create(vals)
            _logger.info(
                '_ensure_mappings_for_flujos: mapping creado para flujo=%s',
                flujo.name)

    @api.model
    def aplicar_deteccion_automatica(self, prompt_text):
        """
        Detección híbrida de flujos relevantes según el system_prompt del cliente.

        1. Normaliza el prompt (minúsculas, sin acentos).
        2. Keyword matching: cada flujo expone palabras_clave; si alguna aparece
           en el prompt, el flujo aplica.
        3. Si hubo al menos un match: activa los matcheados y el flujo default,
           archiviva los demás (el write() cascada a los Chatwoot Mappings).
        4. Si NINGÚN flujo matcheó y el prompt no está vacío, llama a la IA
           (gpt.service.detectar_flujos_por_prompt) como respaldo.
        5. Si la IA falla o no hay otro criterio, NO archivar nada (comportamiento
           conservador: se mantiene el estado actual).

        El flujo 'flujo_agendamiento_default' siempre queda activo (fallback).
        """
        prompt_text = prompt_text or ''
        prompt_norm = _normalizar_texto(prompt_text)

        if not prompt_text.strip():
            _logger.info(
                'Detección de flujos: system_prompt vacío, sin cambios '
                '(se mantienen todos los flujos actuales).')
            return {'activados': [], 'archivados': [], 'metodo': 'ninguno',
                    'mensaje': 'Prompt vacío: no se modificaron flujos.'}

        flujos = self.sudo().with_context(active_test=False).search([])
        default_flow = flujos.filtered(lambda f: f.name == 'flujo_agendamiento_default')

        activados = []
        archivados = []
        sin_keywords = []
        for flujo in flujos:
            if flujo in default_flow:
                continue
            keywords = [k.strip() for k in (flujo.palabras_clave or '').split(',')]
            keywords = [_normalizar_texto(k) for k in keywords if k]
            if not keywords:
                # Sin palabras clave no hay criterio de match: se conserva el
                # estado actual para no tocar flujos personalizados.
                sin_keywords.append(flujo.name)
                continue
            # Match de palabra completa (bordes \b) para evitar falsos
            # positivos por subcadena (ej: "salud" dentro de "SALUDO").
            pattern = '|'.join(r'\b' + re.escape(k) + r'\b' for k in keywords)
            if re.search(pattern, prompt_norm):
                activados.append(flujo.name)
            else:
                archivados.append(flujo.name)

        if activados:
            # Hubo al menos un match por keywords: aplicar resultado.
            flujos_act = flujos.filtered(lambda f: f.name in activados) | default_flow
            flujos_arch = flujos.filtered(lambda f: f.name in archivados)
            flujos_act.write({'active': True})
            flujos_arch.write({'active': False})
            self._ensure_mappings_for_flujos(flujos_act)
            flujos_act.action_regenerar_pasos()
            self._sincronizar_mappings(flujos_act, True)
            self._sincronizar_mappings(flujos_arch, False)
            _logger.info(
                'auto_detección (keywords): activados=%s archivados=%s',
                [f.name for f in flujos_act], [f.name for f in flujos_arch])
            return {'activados': [f.name for f in flujos_act],
                    'archivados': [f.name for f in flujos_arch],
                    'metodo': 'keywords', 'mensaje': 'Detección por palabras clave.'}

        # 0 matches con keywords -> respaldo IA (híbrido).
        # Solo flujos con keywords participan en la decisión IA.
        flujos_info = [{'name': f.name,
                        'descripcion_intencion': f.descripcion_intencion or '',
                        'palabras_clave': f.palabras_clave or ''}
                       for f in flujos if f.name != 'flujo_agendamiento_default']
        try:
            gpt_service = self.env.get('gpt.service')
            if not gpt_service:
                raise Exception('Módulo ai_chatbot_0_core no disponible')
            recomendados = gpt_service.sudo().detectar_flujos_por_prompt(
                prompt_text, flujos_info)
        except Exception as e:
            _logger.warning(
                'auto_detección: falló la IA de respaldo (%s). Sin cambios.',
                e)
            return {'activados': [], 'archivados': [],
                    'metodo': 'ia_error',
                    'mensaje': 'Falló la detección IA: sin cambios.'}

        activados_ia = [r for r in (recomendados or [])
                        if r and isinstance(r, str)]
        if not activados_ia:
            _logger.warning('auto_detección: la IA no recomendó ningún flujo. Sin cambios.')
            return {'activados': [], 'archivados': [],
                    'metodo': 'ia_sin_recomendaciones',
                    'mensaje': 'La IA no recomendó flujos: se mantuvo la configuración actual.'}
        flujos_act = flujos.filtered(lambda f: f.name in activados_ia) | default_flow
        flujos_arch = flujos.filtered(
            lambda f: f.name not in activados_ia
            and f not in default_flow
            and f.name not in sin_keywords)
        flujos_act.write({'active': True})
        flujos_arch.write({'active': False})
        self._ensure_mappings_for_flujos(flujos_act)
        flujos_act.action_regenerar_pasos()
        self._sincronizar_mappings(flujos_act, True)
        self._sincronizar_mappings(flujos_arch, False)
        _logger.info(
            'auto_detección (IA): activados=%s archivados=%s',
            [f.name for f in flujos_act], [f.name for f in flujos_arch])
        return {'activados': [f.name for f in flujos_act],
                'archivados': [f.name for f in flujos_arch],
                'metodo': 'ia', 'mensaje': 'Detección por IA de respaldo.'}

    @api.model_create_multi
    def create(self, vals_list):
        """
        Crea flujos con sus pasos personalizados según el nombre.
        """
        # Autocompletar grupo/equipo según el nombre del flujo
        mapeo = self._get_mapeo_equipo_grupo()
        for vals in vals_list:
            name = vals.get("name", "")
            if not vals.get('routing_key'):
                vals['routing_key'] = name or ''
            nombre_grupo = None
            if name in mapeo:
                nombre_grupo = mapeo[name]
            # Si hay un nombre de grupo, intentar mapearlo al crm.team
            if nombre_grupo and not vals.get('team_id'):
                # buscar equipo existente
                team = self.env['crm.team'].search([('name', '=', nombre_grupo)], limit=1)
                if not team:
                    # crear equipos CRM si es necesario
                    try:
                        teams = self.env['ai_chatbot_1_portal.chatbot_flujo'] if False else None
                    except Exception:
                        teams = None
                    # usar utilitario para crear/obtener equipos (si está disponible)
                    try:
                        teams_dict = self.env['chatbot.flujo']._get_mapeo_equipo_grupo()
                    except Exception:
                        teams_dict = {}
                    # fallback: buscar/crear por nombre
                    team = self.env['crm.team'].search([('name', '=', nombre_grupo)], limit=1)
                    if not team:
                        try:
                            team = self.env['crm.team'].create({'name': nombre_grupo, 'active': True})
                        except Exception:
                            team = False
                if team:
                    vals['team_id'] = team.id
            # Mantener compatibilidad: asignar equipo textual antiguo si no se pasa
            if not vals.get('grupo_asignado') and name in mapeo:
                vals["grupo_asignado"] = mapeo[name]
        
        flujos = super().create(vals_list)
        
        for flujo in flujos:
            if not flujo.paso_ids and flujo.generar_pasos_automatico:
                flujo._crear_pasos_para_flujo(incluir_opcionales=True)
        
        return flujos
    
    @api.onchange("name")
    def _onchange_name_grupo_asignado(self):
        """
        Autocompleta grupo_asignado al cambiar el nombre del flujo
        en el formulario, permitiendo override manual.
        """
        if self.name:
            mapeo = self._get_mapeo_equipo_grupo()
            if self.name in mapeo:
                nombre_grupo = mapeo[self.name]
                if nombre_grupo:
                    # intentar asignar team_id
                    team = self.env['crm.team'].search([('name', '=', nombre_grupo)], limit=1)
                    if not team:
                        try:
                            team = self.env['crm.team'].create({'name': nombre_grupo, 'active': True})
                        except Exception:
                            team = False
                    if team:
                        self.team_id = team
                # mantener también el campo textual para compatibilidad
                self.grupo_asignado = mapeo.get(self.name)
    
    def copy(self, default=None):
        """
        Al duplicar un flujo, también duplicamos sus pasos.
        """
        default = dict(default or {})
        default['name'] = f"{self.name} (copia)"
        
        nuevo_flujo = super().copy(default)
        
        # Copiar los pasos del flujo original al nuevo
        for paso in self.paso_ids:
            paso.copy(default={'flujo_id': nuevo_flujo.id})
        
        return nuevo_flujo
    
    def action_agregar_pasos_opcionales(self):
        """
        Acción para agregar pasos opcionales a un flujo existente.
        """
        for flujo in self:
            nombres_existentes = flujo.paso_ids.mapped('nombre_interno')
            pasos_opcionales = flujo._get_pasos_opcionales()
            
            Paso = self.env["chatbot.paso"]
            for paso_data in pasos_opcionales:
                if paso_data['nombre_interno'] not in nombres_existentes:
                    paso_vals = paso_data.copy()
                    paso_vals["flujo_id"] = flujo.id
                    Paso.create(paso_vals)
        
        return True
