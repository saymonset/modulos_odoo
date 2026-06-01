from odoo import api, fields, models


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
                "es_requerido": True,
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
                "es_requerido": True,
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
                "nombre_mostrar": "¿Eres paciente nuevo?",
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
                "mensaje_prompt": "¿Te interesa la Tarjeta Salud? (sí/no)",
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
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "🪪 Por favor, envíe una imagen o foto de su cédula o pasaporte.\n🔒 Tus datos están protegidos bajo nuestra política de privacidad.\n📌 Asegúrate de que la imagen sea clara.",
                "mensaje_error": "Por favor envía una imagen clara de tu cédula o pasaporte.",
            },
            {
                "secuencia": 14,
                "nombre_interno": "solicitar_consulta_deseada",
                "nombre_mostrar": "Consulta o estudio deseado",
                "tipo_dato": "text",
                "campo_destino": "consulta_deseada",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "🔍 Indícanos la consulta o estudio que deseas realizarte.\n\nPuedes escribir algo como:\n✏️ 'Consulta de medicina general'\n✏️ 'Ecografía abdominal'\n✏️ 'Examen de sangre'\n✏️ 'Consulta con pediatra'",
                "mensaje_error": "Por favor indica qué consulta o estudio deseas.",
            },
        ])
        return pasos
    
    def _get_pasos_para_seguro(self):
        """
        Pasos específicos para el flujo flujo_citas_seguro
        """
        pasos = self._get_pasos_obligatorios()
        pasos.extend([
            {
                "secuencia": 12.5,
                "nombre_interno": "solicitar_nombre_seguro",
                "nombre_mostrar": "Nombre del seguro médico",
                "tipo_dato": "text",
                "campo_destino": "nombre_seguro",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "🩺 Has indicado que usarás un seguro médico.\nPor favor, escríbeme el nombre completo de tu seguro para poder validar la cobertura y agendar tu cita sin contratiempos. ✅\n\n✏️ Ejemplos:\n    • FASME\n    • FASDEM\n    • SENIAT\n    • ALCALDIA DE MANEIRO\n    • LA INTERNACIONAL\n\n📌 Si tu seguro no está en convenio con UNISA, nuestro equipo te informará las opciones de pago particular.",
                "mensaje_error": "Por favor indica el nombre de tu seguro médico.",
            },
            {
                "secuencia": 20,
                "nombre_interno": "solicitar_foto_vat",
                "nombre_mostrar": "Foto de cédula o pasaporte",
                "tipo_dato": "image",
                "campo_destino": "foto_vat",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "🪪 Por favor, envíe una imagen o foto de su cédula o pasaporte.\n🔒 Tus datos están protegidos bajo nuestra política de privacidad.\n📌 Asegúrate de que la imagen sea clara.",
                "mensaje_error": "Por favor envía una imagen clara de tu cédula o pasaporte.",
            },
            {
                "secuencia": 14,
                "nombre_interno": "solicitar_consulta_deseada",
                "nombre_mostrar": "Consulta o estudio deseado",
                "tipo_dato": "text",
                "campo_destino": "consulta_deseada",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "🔍 Indícanos la consulta o estudio que deseas realizarte.\n\nPuedes escribir algo como:\n✏️ 'Consulta de medicina general'\n✏️ 'Ecografía abdominal'\n✏️ 'Examen de sangre'\n✏️ 'Consulta con pediatra'",
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
                "secuencia": 10,
                "nombre_interno": "solicitar_identificacion",
                "nombre_mostrar": "Identificación del paciente",
                "tipo_dato": "text",
                "campo_destino": "identificacion_paciente",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "📄 Por favor, escribe el nombre completo y cédula del paciente:",
                "mensaje_error": "Por favor proporciona nombre completo y cédula.",
            },
            {
                "secuencia": 11,
                "nombre_interno": "solicitar_estudio",
                "nombre_mostrar": "Estudio solicitado",
                "tipo_dato": "text",
                "campo_destino": "estudio_solicitado",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "📄 ¿Qué estudio de laboratorio necesitas? (Ej: Hemoglobina, Glucosa, Colesterol, Examen de orina, etc.)",
                "mensaje_error": "Por favor indica qué estudio necesitas.",
            },
        ]
    
    def _get_pasos_para_resultados_imagenes(self):
        """
        Pasos específicos para flujo_resultados_imagenes
        """
        return [
            {
                "secuencia": 10,
                "nombre_interno": "solicitar_identificacion",
                "nombre_mostrar": "Identificación del paciente",
                "tipo_dato": "text",
                "campo_destino": "identificacion_paciente",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "📄 Por favor, escribe el nombre completo y cédula del paciente:",
                "mensaje_error": "Por favor proporciona nombre completo y cédula.",
            },
            {
                "secuencia": 11,
                "nombre_interno": "solicitar_estudio",
                "nombre_mostrar": "Estudio solicitado",
                "tipo_dato": "text",
                "campo_destino": "estudio_solicitado",
                "es_requerido": True,
                "es_paso_telefono": False,
                "mensaje_prompt": "📄 ¿Qué estudio de imágenes necesitas? (Ej: Radiografía, Ecografía, Mamografía, Tomografía, etc.)",
                "mensaje_error": "Por favor indica qué estudio necesitas.",
            },
        ]
    
    def _get_todos_los_pasos(self):
        """Retorna TODOS los pasos (obligatorios + opcionales) para flujos genéricos"""
        return self._get_pasos_obligatorios() + self._get_pasos_opcionales()
    
    # ============================================================
    # MÉTODOS PARA CREAR PASOS EN UN FLUJO (VERSIÓN PERSONALIZADA)
    # ============================================================
    
    def _crear_pasos_para_flujo(self, incluir_opcionales=True):
        """
        Crea los pasos para este flujo.
        Según el nombre del flujo, usa pasos diferentes.
        """
        Paso = self.env["chatbot.paso"]
        
        # SELECCIONAR PASOS SEGÚN EL NOMBRE DEL FLUJO (coincide con n8n)
        if self.name == "flujo_citas_medios_propios":
            pasos_data = self._get_pasos_para_medios_propios()
        elif self.name == "flujo_citas_seguro":
            pasos_data = self._get_pasos_para_seguro()
        elif self.name == "flujo_resultados_laboratorio":
            pasos_data = self._get_pasos_para_resultados_lab()
        elif self.name == "flujo_resultados_imagenes":
            pasos_data = self._get_pasos_para_resultados_imagenes()
        elif self.name == "flujo_agendamiento_precios":
            # Flujo informativo: mostrar información de precios primero.
            # No solicitamos teléfono como primer paso; el usuario puede
            # confirmar que desea agendar y entonces iniciar el flujo de agendamiento.
            pasos_data = [
                {
                    "secuencia": 1,
                    "nombre_interno": "informar_precios",
                    "nombre_mostrar": "Información de precios",
                    "tipo_dato": "text",
                    "campo_destino": "informacion_precios",
                    "es_requerido": False,
                    "es_paso_telefono": False,
                    "mensaje_prompt": "Conoce nuestros precios básicos 2026. ¿Deseas que te ayudemos a agendar una cita? Responde 'Sí' para continuar.",
                    "mensaje_error": "",
                }
            ]
        else:
            # Flujos genéricos: flujo_agendamiento_directo, flujo_agendamiento_precios, 
            # flujo_agendamiento_servicios, flujo_agendamiento_otra_consulta, 
            # flujo_ventas_unisa, flujo_agendamiento_default
            if incluir_opcionales:
                pasos_data = self._get_todos_los_pasos()
            else:
                pasos_data = self._get_pasos_obligatorios()
        
        for paso_data in pasos_data:
            paso_vals = paso_data.copy()
            paso_vals["flujo_id"] = self.id
            Paso.create(paso_vals)
        
        return True
    
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
            "Agendamiento_Directo": "información general y ubicación",
            "flujo_agendamiento_directo": "información general y ubicación",
            "Agendamiento_Precios": "información de precios y promociones",
            "flujo_agendamiento_precios": "información de precios y promociones",
            "Agendamiento_Servicios": "información sobre nuestros servicios",
            "flujo_agendamiento_servicios": "información sobre nuestros servicios",
            "Agendamiento_Otra_Consulta": "consultas generales",
            "flujo_agendamiento_otra_consulta": "consultas generales",
            "Agendamiento_Tarjeta": "ventas y afiliación a nuestra tarjeta",
            "flujo_ventas_unisa": "ventas y afiliación a nuestra tarjeta",
            "Ventas_UNISA": "ventas y afiliación a nuestra tarjeta",
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
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Crea flujos con sus pasos personalizados según el nombre.
        """
        # Autocompletar grupo/equipo según el nombre del flujo
        mapeo = self._get_mapeo_equipo_grupo()
        for vals in vals_list:
            name = vals.get("name", "")
            nombre_grupo = None
            if name in mapeo:
                nombre_grupo = mapeo[name]
            # Si hay un nombre de grupo, intentar mapearlo al crm.team
            if nombre_grupo and not vals.get('team_id'):
                # buscar equipo existente
                team = self.env['crm.team'].search([('name', '=', nombre_grupo)], limit=1)
                if not team:
                    # crear equipos UNISA si es necesario
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
            if not flujo.paso_ids:
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
