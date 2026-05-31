# -*- coding: utf-8 -*-
# Archivo: unisa_chatbot_utils.py
from datetime import datetime
import json
import logging
import requests
from odoo import fields, _
import re
import base64

_logger = logging.getLogger(__name__)

class ChatBotUtils:
    
    @staticmethod
    def create_attachment(env, url, name, res_model, res_id):
        """Crear adjunto a partir de URL (Versión Python 3)"""
        try:
            _logger.info("Creando adjunto '%s' desde URL para %s:%s", name, res_model, res_id)
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                attachment = env['ir.attachment'].sudo().create({
                    'name': name,
                    'type': 'binary',
                    'datas': base64.b64encode(response.content).decode('ascii'),
                    'res_model': res_model,
                    'res_id': res_id,
                    'mimetype': response.headers.get('Content-Type', 'image/jpeg')
                })
                return attachment
        except Exception as e:
            _logger.error(f"Error creando adjunto {name}: {str(e)}")
        return None

    @staticmethod
    def convert_fecha_nacimiento(fecha_str):
        """Convierte fecha a formato yyyy-mm-dd para Odoo, aceptando múltiples formatos de entrada."""
        if not fecha_str:
            return False

        formatos = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%d.%m.%Y',
        ]

        for fmt in formatos:
            try:
                fecha_obj = datetime.strptime(fecha_str, fmt)
                return fecha_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue

        _logger.error(f"Error convirtiendo fecha {fecha_str}: formato no reconocido")
        return False

    @staticmethod
    def convert_date(date_str):
        """Convertir fecha de formato dd/mm/yyyy a yyyy-mm-dd"""
        try:
            if date_str and '/' in date_str:
                day, month, year = date_str.split('/')
                return f"{year}-{month}-{day}"
        except:
            pass
        return False

    @staticmethod
    def normalizar_telefono_internacional(phone):
        """
        Normaliza un número de teléfono a formato internacional con +58.
        Ejemplos:
        - 04141234567 → +584141234567
        - 4141234567 → +584141234567
        - +584141234567 → +584141234567 (se mantiene)
        - 584141234567 → +584141234567
        - 0412-1234567 → +584121234567
        """
        if not phone:
            return ''
        
        phone_str = str(phone).strip()
        digits = ''.join(filter(str.isdigit, phone_str))
        
        if not digits:
            return phone_str
        
        # Si ya tiene el formato con + y 58, devolverlo
        if phone_str.startswith('+58') and len(digits) >= 11:
            return f"+{digits}"
        
        # Si tiene 58 al inicio (sin +)
        if digits.startswith('58') and len(digits) >= 11:
            return f"+{digits}"
        
        # Si comienza con 0 (ej: +584141234567)
        if digits.startswith('0') and len(digits) >= 11:
            return f"+58{digits[1:]}"
        
        # Si tiene 10 dígitos y comienza con 4 (ej: 4141234567)
        if len(digits) == 10 and digits.startswith('4'):
            return f"+58{digits}"
        
        # Si tiene menos de 10 dígitos, devolver como está
        if len(digits) < 10:
            return phone_str
        
        # Fallback: agregar +58
        return f"+58{digits}"

    @staticmethod
    def find_partner_by_phone(env, phone):
        """
        Busca un partner por teléfono usando comparación de dígitos.
        Esto permite encontrar coincidencias independientemente del formato.
        """
        if not phone:
            return None
        
        # Extraer solo dígitos del teléfono ingresado
        phone_digits = ''.join(filter(str.isdigit, phone))
        if not phone_digits or len(phone_digits) < 7:
            _logger.warning("Teléfono inválido o muy corto: %s", phone)
            return None
        
        _logger.info("=== BUSCANDO PARTNER POR TELÉFONO ===")
        _logger.info("Teléfono original: %s", phone)
        _logger.info("Dígitos extraídos: %s", phone_digits)
        
        partner = None
        
        # ESTRATEGIA 1: Buscar por últimos 10 dígitos
        search_term = phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits
        if len(search_term) >= 7:
            _logger.info("Estrategia 1 - Buscando por sufijo: %s", search_term)
            partner = env['res.partner'].sudo().search([
                ('phone', '=like', f'%{search_term}'),
                ('active', '=', True)
            ], limit=1)
            if partner:
                _logger.info("✅ Partner encontrado por sufijo: %s (ID: %s) - Tel: %s", 
                             partner.name, partner.id, partner.phone)
                return partner
        
        # ESTRATEGIA 2: Buscar por dígitos completos
        _logger.info("Estrategia 2 - Buscando por dígitos completos: %s", phone_digits)
        partner = env['res.partner'].sudo().search([
            ('phone', 'ilike', phone_digits),
            ('active', '=', True)
        ], limit=1)
        if partner:
            _logger.info("✅ Partner encontrado por dígitos completos: %s (ID: %s) - Tel: %s", 
                         partner.name, partner.id, partner.phone)
            return partner
        
        # ESTRATEGIA 3: Buscar por últimos 8 dígitos
        if len(phone_digits) >= 8:
            search_term_8 = phone_digits[-8:]
            _logger.info("Estrategia 3 - Buscando por últimos 8 dígitos: %s", search_term_8)
            partner = env['res.partner'].sudo().search([
                ('phone', '=like', f'%{search_term_8}'),
                ('active', '=', True)
            ], limit=1)
            if partner:
                _logger.info("✅ Partner encontrado por últimos 8 dígitos: %s (ID: %s) - Tel: %s", 
                             partner.name, partner.id, partner.phone)
                return partner
        
        # ESTRATEGIA 4: Búsqueda manual por comparación de dígitos
        _logger.info("Estrategia 4 - Búsqueda manual por comparación de dígitos")
        all_partners = env['res.partner'].sudo().search([
            ('phone', '!=', False),
            ('active', '=', True)
        ], limit=100)
        
        for p in all_partners:
            if p.phone:
                p_digits = ''.join(filter(str.isdigit, p.phone))
                # Verificar si los dígitos coinciden (últimos 7-10 dígitos)
                if p_digits.endswith(phone_digits) or phone_digits.endswith(p_digits[-8:]):
                    _logger.info("✅ Partner encontrado por comparación manual: %s (ID: %s) - Tel BD: %s - Dígitos BD: %s", 
                                 p.name, p.id, p.phone, p_digits)
                    return p
        
        _logger.warning("❌ No se encontró partner para teléfono: %s", phone)
        return None

    @staticmethod
    def update_create_contact(env, data):
        """
        Busca o crea un contacto basado en VAT o Teléfono.
        Actualiza SOLO los campos que tienen valor (no sobreescribe vacíos con vacíos).
        """
        phone_raw = data.get('solicitar_phone', '').strip()
        phone = ChatBotUtils.normalizar_telefono_internacional(phone_raw) if phone_raw else ''
        
        name = data.get('solicitar_name', '').strip()
        vat = data.get('solicitar_vat', '').strip()
        birthdate = data.get('solicitar_birthdate', '').strip()
        email = data.get('solicitar_email', '').strip()
        consentimiento_raw = data.get('consentimiento', False)

        # Convertir consentimiento a booleano
        if isinstance(consentimiento_raw, str):
            consentimiento = consentimiento_raw.lower() in ['true', '1', 'sí', 'si', 'yes']
        else:
            consentimiento = bool(consentimiento_raw)

        partner = None
        
        # 1. Buscar por VAT
        if vat:
            partner = env['res.partner'].sudo().search([('vat', '=', vat)], limit=1)
            if partner:
                _logger.info("Contacto encontrado por VAT: %s", vat)

        # 2. Buscar por teléfono
        if not partner and phone:
            partner = ChatBotUtils.find_partner_by_phone(env, phone)
            if partner:
                _logger.info("Contacto encontrado por Teléfono: %s", phone)

        # Preparar datos del partner (SOLO campos que tienen valor)
        partner_data = {}
        
        if name:
            partner_data['name'] = name
        if vat:
            partner_data['vat'] = vat
        if phone:
            partner_data['phone'] = phone
        if email:
            partner_data['email'] = email
        
        partner_data['type'] = 'contact'
        partner_data['company_type'] = 'person'
        partner_data['consentimiento_whatsapp'] = consentimiento

        # Fecha de nacimiento
        if birthdate:
            fecha_convertida = ChatBotUtils.convert_fecha_nacimiento(birthdate)
            if fecha_convertida and 'birthdate' in env['res.partner']._fields:
                partner_data['birthdate'] = fecha_convertida

        if partner:
            # Actualizar contacto existente (solo campos que tienen valor)
            if partner_data:
                partner.sudo().write(partner_data)
                _logger.info("Contacto ACTUALIZADO: ID %s - Campos actualizados: %s", partner.id, list(partner_data.keys()))
            else:
                _logger.info("No hay datos nuevos para actualizar el contacto ID %s", partner.id)
        else:
            # Crear nuevo contacto
            if not partner_data.get('name'):
                partner_data['name'] = f"Contacto {phone or vat or 'Nuevo'}"
            partner = env['res.partner'].sudo().create(partner_data)
            _logger.info("Contacto CREADO: ID %s - Datos: %s", partner.id, list(partner_data.keys()))

        return partner

    @staticmethod
    def search_contact(env, data):
        """Búsqueda de contacto únicamente por teléfono."""
        phone = data.get('telefono', data.get('solicitar_phone', '')).strip()
        return ChatBotUtils.find_partner_by_phone(env, phone)

    @staticmethod
    def get_ultima_cita(env, partner_id):
        """Obtiene información de la última cita del paciente"""
        ultima_cita = env['crm.lead'].search([
            ('partner_id', '=', partner_id),
            ('type', '=', 'opportunity'),
            ('active', '=', True)
        ], order='create_date desc', limit=1)
        if ultima_cita:
            return {
                'fecha': ultima_cita.create_date.strftime('%d/%m/%Y'),
                'servicio': ultima_cita.name,
                'estado': ultima_cita.stage_id.name if ultima_cita.stage_id else 'Finalizado'
            }
        return None

    @staticmethod
    def get_team_unisa(env):
        """Obtener o crear equipos de UNISA (Grupo Citas, Grupo Ventas, Grupo Laboratorio, Grupo Imagenología)"""
        teams = {}
        team_names = ['Grupo Citas', 'Grupo Ventas', 'Grupo Laboratorio', 'Grupo Imagenología']
        for team_name in team_names:
            team = env['crm.team'].search([('name', '=', team_name)], limit=1)
            if not team:
                try:
                    team_data = {
                        'name': team_name,
                        'active': True,
                        'member_ids': False,
                    }
                    if team_name == 'Grupo Citas':
                        team_data['alias_name'] = 'citas-unisa'
                    elif team_name == 'Grupo Ventas':
                        team_data['alias_name'] = 'ventas-unisa'
                    elif team_name == 'Grupo Laboratorio':
                        team_data['alias_name'] = 'laboratorio-unisa'
                    elif team_name == 'Grupo Imagenología':
                        team_data['alias_name'] = 'imagenologia-unisa'
                    team = env['crm.team'].create(team_data)
                    _logger.info(f"✅ Equipo UNISA creado: {team.name} (ID: {team.id})")
                except Exception as e:
                    _logger.error(f"❌ Error creando equipo {team_name}: {str(e)}")
                    team = env['crm.team'].search([('active', '=', True)], limit=1)
                    if not team:
                        team = env['crm.team'].create({'name': team_name + ' (Fallback)', 'active': True})
                        _logger.warning(f"⚠️ Se creó equipo genérico: {team.name}")
            else:
                _logger.info(f"✅ Equipo UNISA encontrado: {team.name} (ID: {team.id})")
            teams[team_name] = team
        return teams

    @staticmethod
    def setup_utm(env, platform='whatsapp'):
        """Configurar medium, source y campaign según la plataforma"""
        platform = platform.lower().strip() if platform else 'whatsapp'
        platform_names = {
            'whatsapp': 'WhatsApp', 'instagram': 'Instagram', 'telegram': 'Telegram',
            'facebook': 'Facebook', 'messenger': 'Facebook Messenger', 'web': 'Web', 'sms': 'SMS'
        }
        platform_display = platform_names.get(platform, platform.title())
        medium = env['utm.medium'].search([('name', '=ilike', platform_display)], limit=1)
        if not medium:
            medium = env['utm.medium'].create({'name': platform_display})
        source_name = f"{platform_display} Bot UNISA"
        source = env['utm.source'].search([('name', '=ilike', source_name)], limit=1)
        if not source:
            source = env['utm.source'].create({'name': source_name})
        campaign_name = f"Campaña {platform_display} UNISA"
        campaign = env['utm.campaign'].search([('name', '=ilike', campaign_name)], limit=1)
        if not campaign:
            campaign = env['utm.campaign'].create({'name': campaign_name})
        _logger.info(f"✅ UTM configurado para plataforma: {platform_display}")
        return medium, source, campaign

    @staticmethod
    def get_or_create_bot_tag(env, platform='whatsapp'):
        """Obtener o crear etiqueta para leads del bot según plataforma"""
        platform = platform.lower().strip() if platform else 'whatsapp'
        platform_config = {
            'whatsapp': {'name': 'WhatsApp Bot', 'color': 10},
            'instagram': {'name': 'Instagram Bot', 'color': 9},
            'telegram': {'name': 'Telegram Bot', 'color': 2},
            'facebook': {'name': 'Facebook Bot', 'color': 4},
            'messenger': {'name': 'Messenger Bot', 'color': 4}
        }
        config = platform_config.get(platform, {'name': f"{platform.title()} Bot", 'color': 1})
        tag = env['crm.tag'].sudo().search([('name', '=ilike', config['name'])], limit=1)
        if not tag:
            tag = env['crm.tag'].sudo().create({'name': config['name'], 'color': config['color']})
            _logger.info(f"✅ Etiqueta creada para {platform}: {tag.name}")
        return tag

    @staticmethod
    def create_lead(env, data, partner, team, medium, source, campaign, tag):
        """Crear lead en CRM con email y consentimiento en la descripción"""
        description = ChatBotUtils.generate_description(data)
        servicio = data.get('servicio_solicitado') or data.get('solicitar_servicio', 'Consulta')
        nombre = data.get('name') or data.get('solicitar_name', 'Sin nombre')
        lead_name = f"{servicio} - {nombre}"
        
        # Agregar equipo responsable a la descripción
        equipo_asignado = data.get('equipo_asignado', '')
        descripcion_grupos = {
            'Agendamiento_Directo': 'información general y ubicación',
            'flujo_agendamiento_directo': 'información general y ubicación',
            'Agendamiento_Precios': 'información de precios y promociones',
            'flujo_agendamiento_precios': 'información de precios y promociones',
            'Agendamiento_Servicios': 'información sobre nuestros servicios',
            'flujo_agendamiento_servicios': 'información sobre nuestros servicios',
            'Agendamiento_Otra_Consulta': 'consultas generales',
            'flujo_agendamiento_otra_consulta': 'consultas generales',
            'Agendamiento_Tarjeta': 'ventas y afiliación a nuestra tarjeta',
            'flujo_ventas_unisa': 'ventas y afiliación a nuestra tarjeta',
            'CITAS_MP': 'citas por medios propios',
            'flujo_citas_medios_propios': 'citas por medios propios',
            'CITAS_SEGUROS': 'citas con seguro médico',
            'flujo_citas_seguro': 'citas con seguro médico',
            'RESULTADOS_LAB': 'resultados de laboratorio',
            'flujo_resultados_laboratorio': 'resultados de laboratorio',
            'RESULTADOS_IMAGENES': 'resultados de imagenología',
            'flujo_resultados_imagenes': 'resultados de imagenología',
        }
        area_texto = descripcion_grupos.get(equipo_asignado, '')
        if area_texto:
            description += f"\n\n**👥 ÁREA RESPONSABLE:** {area_texto.capitalize()}"
        if team:
            description += f"\n**🏥 EQUIPO ASIGNADO:** {team.name}"
        
        # Normalizar teléfono para lead
        phone_raw = data.get('phone') or data.get('solicitar_phone', '')
        phone_normalizado = ChatBotUtils.normalizar_telefono_internacional(phone_raw)
        # Para el lead, mostrar sin +58 (para WhatsApp local)
        phone_lead = phone_normalizado.replace('+58', '') if phone_normalizado.startswith('+58') else phone_normalizado
        email = data.get('email') or data.get('solicitar_email', partner.email or '')
        
        lead_data = {
            'name': lead_name,
            'partner_id': partner.id,
            'contact_name': nombre,
            'email_from': email,
            'phone': phone_lead,
            'description': description,
            'medium_id': medium.id,
            'source_id': source.id,
            'campaign_id': campaign.id,
            'team_id': team.id if team else False,
            'tag_ids': [(4, tag.id)],
            'type': 'opportunity',
            'stage_id': ChatBotUtils.get_default_stage(env),
        }
        lead = env['crm.lead'].create(lead_data)
        fecha_creacion = lead.create_date.strftime('%d/%m/%Y') if lead.create_date else datetime.now().strftime('%d/%m/%Y')
        lead.write({'name': f"{lead.name} - ID {lead.id} ({fecha_creacion})"})
        _logger.info(f"Lead creado: ID {lead.id} - {lead.name}")
        return lead

    @staticmethod
    def create_resultados_lead(env, data, team, medium, source, campaign, tag):
        """
        Crear lead específico para resultados de laboratorio o imágenes
        Incluye toda la información recogida del paciente durante la conversación.
        """
        identificacion = (
            data.get('identificacion_paciente') or 
            data.get('solicitar_identificacion') or 
            data.get('solicitar_name') or 
            data.get('name') or 
            'Sin identificación'
        )
        estudio = (
            data.get('estudio_solicitado') or 
            data.get('solicitar_estudio') or 
            'No especificado'
        )
        equipo_asignado = data.get('equipo_asignado', 'RESULTADOS_LAB')
        
        tipo_estudio = "LABORATORIO" if equipo_asignado in ['RESULTADOS_LAB', 'flujo_resultados_laboratorio'] else "IMAGENOLOGÍA"
        
        lead_name = f"Resultados {tipo_estudio} - {estudio[:50]}"
        
        # === SECCIÓN 1: Encabezado del tipo de solicitud ===
        description = f"""**SOLICITUD DE RESULTADOS - {tipo_estudio}**

• Identificación del paciente: {identificacion}
• Estudio solicitado: {estudio}
• Plataforma: {data.get('plataforma', 'WhatsApp')}
• Fecha de solicitud: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        
        # === SECCIÓN 2: Todos los datos del paciente recogidos durante el flujo ===
        info_adicional = []
        
        name = data.get('solicitar_name') or data.get('name', '')
        if name:
            info_adicional.append(f"• Nombre completo: {name}")
        
        vat = data.get('solicitar_vat') or data.get('vat', '')
        if vat:
            info_adicional.append(f"• Cédula: {vat}")
        
        phone = data.get('solicitar_phone') or data.get('phone', '')
        if phone:
            info_adicional.append(f"• Teléfono: {phone}")
        
        email = data.get('solicitar_email') or data.get('email', '')
        if email:
            info_adicional.append(f"• Correo electrónico: {email}")
        
        birthdate = data.get('solicitar_birthdate') or data.get('birthdate', '')
        if birthdate:
            info_adicional.append(f"• Fecha de nacimiento: {birthdate}")
        
        consentimiento = data.get('consentimiento') or data.get('consentimiento_whatsapp', False)
        if consentimiento:
            consent_value = 'Sí' if str(consentimiento).lower() in ['true', '1', 'sí', 'si', 'yes'] else str(consentimiento)
            info_adicional.append(f"• Consentimiento WhatsApp: {consent_value}")
        
        servicio = data.get('solicitar_servicio') or data.get('servicio_solicitado', '')
        if servicio:
            info_adicional.append(f"• Servicio solicitado: {servicio}")
        
        consulta = data.get('solicitar_consulta_deseada') or data.get('consulta_deseada', '')
        if consulta:
            info_adicional.append(f"• Consulta deseada: {consulta}")
        
        seguro = data.get('solicitar_nombre_seguro') or data.get('nombre_seguro', '')
        if seguro:
            info_adicional.append(f"• Seguro: {seguro}")
        
        fecha_pref = data.get('solicitar_fecha_preferida') or data.get('fecha_preferida', '')
        if fecha_pref:
            info_adicional.append(f"• Fecha preferida: {fecha_pref}")
        
        hora = data.get('solicitar_hora_preferida') or data.get('hora_preferida', '')
        if hora:
            info_adicional.append(f"• Horario: {hora}")
        
        medio_pago = data.get('solicitar_medio_pago') or data.get('medio_pago', '')
        if medio_pago:
            info_adicional.append(f"• Medio de pago: {medio_pago}")
        
        es_nuevo = data.get('solicitar_es_paciente_nuevo') or data.get('es_paciente_nuevo', '')
        if es_nuevo:
            es_nuevo_value = 'Sí' if str(es_nuevo).lower() in ['true', '1', 'sí', 'si', 'yes'] else 'No'
            info_adicional.append(f"• Paciente nuevo: {es_nuevo_value}")
        
        membresia = data.get('solicitar_membresia_interes') or data.get('membresia_interes', '')
        if membresia:
            membresia_value = 'Sí' if str(membresia).lower() in ['true', '1', 'sí', 'si', 'yes'] else 'No'
            info_adicional.append(f"• Interés Tarjeta Salud: {membresia_value}")
        
        if info_adicional:
            description += "\n**📋 DATOS COMPLETOS DEL PACIENTE**\n\n"
            description += "\n".join(info_adicional)
        
        if team:
            description += f"\n\n**🏥 EQUIPO ASIGNADO:** {team.name}"
        
        lead_data = {
            'name': lead_name,
            'contact_name': identificacion,
            'description': description,
            'medium_id': medium.id,
            'source_id': source.id,
            'campaign_id': campaign.id,
            'team_id': team.id if team else False,
            'tag_ids': [(4, tag.id)],
            'type': 'opportunity',
            'stage_id': ChatBotUtils.get_default_stage(env),
        }
        
        lead = env['crm.lead'].create(lead_data)
        fecha_creacion = lead.create_date.strftime('%d/%m/%Y') if lead.create_date else datetime.now().strftime('%d/%m/%Y')
        lead.write({'name': f"{lead.name} - ID {lead.id} ({fecha_creacion})"})
        _logger.info(f"Lead de resultados creado: ID {lead.id} - {lead.name}")
        return lead

    @staticmethod
    def generate_description(data):
        """Generar descripción del lead, incluyendo email y consentimiento."""
        platform = data.get('plataforma', 'WhatsApp')
        if platform.lower() == 'whatsapp':
            platform = 'WhatsApp'
        lines = [f"Cita desde {platform} Bot \n"]

        defaults = {
            'solicitar_fecha_preferida': 'lo antes posible',
            'hora_preferida': 'cualquier hora',
        }

        fields_order = [
            (('solicitar_name', 'name'), 'Paciente'),
            (('solicitar_vat', 'vat'), 'Cédula'),
            (('solicitar_birthdate', 'birthdate'), 'Fecha de nacimiento'),
            (('solicitar_phone', 'phone'), 'Teléfono'),
            (('solicitar_email', 'email'), 'Correo electrónico'),
            (('consentimiento', 'consentimiento_whatsapp'), 'Consentimiento WhatsApp'),
            (('solicitar_servicio', 'servicio_solicitado', 'solicitar_servicio'), 'Servicio'),
            (('solicitar_consulta_deseada', 'consulta_deseada'), 'Consulta deseada'),
            (('solicitar_nombre_seguro', 'nombre_seguro'), 'Nombre del seguro'),
            (('solicitar_fecha_preferida', 'fecha_preferida'), 'Fecha preferida'),
            (('hora_preferida', ), 'Horario'),
            (('solicitar_medio_pago', 'medio_pago'), 'Medio de pago'),
            (('solicitar_es_paciente_nuevo', 'es_paciente_nuevo'), 'Paciente nuevo'),
            (('solicitar_membresia_interes', 'membresia_interes'), 'Interés Tarjeta Salud'),
        ]

        for keys, label in fields_order:
            field = next((k for k in keys if k in data), None)
            if field:
                raw_value = data[field]
                if raw_value is None or raw_value == '':
                    if field in defaults:
                        value = defaults[field]
                    else:
                        continue
                else:
                    value = str(raw_value).strip() if not isinstance(raw_value, bool) else raw_value

                if field in ('consentimiento', 'solicitar_es_paciente_nuevo', 'solicitar_membresia_interes'):
                    if isinstance(value, bool):
                        value = 'Sí' if value else 'No'
                    else:
                        value = 'Sí' if str(value).lower() in ['true', '1', 'sí', 'si', 'yes'] else 'No'

                lines.append(f"• {label}: {value}")

        if len(lines) == 1:
            lines.append("• Sin información adicional")
        return "\n".join(lines)

    @staticmethod
    def get_default_stage(env):
        """Obtener etapa por defecto para leads"""
        stage = env['crm.stage'].search([('name', 'ilike', 'nuevo')], limit=1)
        if not stage:
            stage = env['crm.stage'].search([], limit=1)
        return stage.id if stage else False

    @staticmethod
    def assign_lead_round_robin(env, lead, team):
        """Asignar lead usando round robin"""
        if not team or not team.member_ids:
            return
        try:
            param_name = f'unisa_bot_last_user_{team.id}'
            last_assigned_user_id = env['ir.config_parameter'].sudo().get_param(param_name)
            team_members = team.member_ids.sorted('id')
            if last_assigned_user_id:
                last_user = env['res.users'].browse(int(last_assigned_user_id))
                if last_user in team_members:
                    current_index = team_members.ids.index(last_user.id)
                    next_index = (current_index + 1) % len(team_members)
                    next_user = team_members[next_index]
                else:
                    next_user = team_members[0]
            else:
                next_user = team_members[0]
            lead.write({'user_id': next_user.id})
            env['ir.config_parameter'].sudo().set_param(param_name, next_user.id)
            _logger.info(f"Lead {lead.id} asignado a {next_user.name}")
        except Exception as e:
            _logger.warning(f"Error en round robin: {str(e)}")

    @staticmethod
    def handle_images(env, data, lead, partner):
        """Manejar imágenes adjuntas y publicarlas en el Chatter"""
        _logger.info("Iniciando handle_images para Lead %s y Partner %s", lead.id, partner.id)
        attachment_ids_lead = []
        attachment_ids_partner = []
        
        foto_vat_url = data.get('foto_vat_url') or data.get('solicitar_foto_vat')
        if foto_vat_url and isinstance(foto_vat_url, str) and re.match(r'^https?://', foto_vat_url):
            vat = data.get('solicitar_vat') or 'SIN_CEDULA'
            name_vat = f"Cedula_{vat}_{partner.name or 'Cliente'}.jpg"
            att_lead = ChatBotUtils.create_attachment(env, foto_vat_url, name_vat, 'crm.lead', lead.id)
            if att_lead:
                attachment_ids_lead.append(att_lead.id)
            att_partner = ChatBotUtils.create_attachment(env, foto_vat_url, name_vat, 'res.partner', partner.id)
            if att_partner:
                attachment_ids_partner.append(att_partner.id)
        
        imgs_adicionales = data.get('imagenes_adicionales') or data.get('solicitar_imagenes_adicionales') or []
        if isinstance(imgs_adicionales, str):
            try:
                imgs_adicionales = json.loads(imgs_adicionales)
            except:
                imgs_adicionales = [imgs_adicionales] if imgs_adicionales.startswith('http') else []
        if isinstance(imgs_adicionales, list):
            vat = data.get('solicitar_vat') or 'SIN_CEDULA'
            for i, img_url in enumerate(imgs_adicionales, 1):
                if img_url and isinstance(img_url, str) and re.match(r'^https?://', img_url):
                    name_img = f"Doc_Adicional_{i}_{vat}.jpg"
                    att_l = ChatBotUtils.create_attachment(env, img_url, name_img, 'crm.lead', lead.id)
                    if att_l:
                        attachment_ids_lead.append(att_l.id)
                    att_p = ChatBotUtils.create_attachment(env, img_url, name_img, 'res.partner', partner.id)
                    if att_p:
                        attachment_ids_partner.append(att_p.id)
        
        if attachment_ids_lead:
            lead.sudo().message_post(body=_("Imágenes recibidas desde el Chatbot."), attachment_ids=attachment_ids_lead)
            _logger.info("Publicadas %d imágenes en Chatter del Lead", len(attachment_ids_lead))
        if attachment_ids_partner:
            partner.sudo().message_post(body=_("Imágenes recibidas desde el Chatbot."), attachment_ids=attachment_ids_partner)
            _logger.info("Publicadas %d imágenes en Chatter del Partner", len(attachment_ids_partner))

    @staticmethod
    def validate_image_urls(data):
        """Validar que las URLs de imágenes sean accesibles"""
        validated_data = {
            'foto_vat_url': data.get('foto_vat') or data.get('solicitar_foto_vat', ''),
            'imagenes_adicionales': []
        }
        foto_url = data.get('foto_vat') or data.get('solicitar_foto_vat', '')
        if foto_url and re.match(r'^https?://', foto_url):
            validated_data['foto_vat_url'] = foto_url
        try:
            imagenes_raw = data.get('imagenes_adicionales') or data.get('solicitar_imagenes_adicionales', [])
            if isinstance(imagenes_raw, str):
                imagenes = json.loads(imagenes_raw)
            elif isinstance(imagenes_raw, list):
                imagenes = imagenes_raw
            else:
                imagenes = []
            for img_url in imagenes:
                if img_url and re.match(r'^https?://', img_url):
                    validated_data['imagenes_adicionales'].append(img_url)
        except:
            validated_data['imagenes_adicionales'] = []
        return validated_data

    @staticmethod
    def _pie_mensaje(lead_id, equipo_asignado):
        """Genera el pie del mensaje con datos de referencia."""
        descripcion_grupos = {
            'Agendamiento_Directo': 'información general y ubicación',
            'flujo_agendamiento_directo': 'información general y ubicación',
            'Agendamiento_Precios': 'información de precios y promociones',
            'flujo_agendamiento_precios': 'información de precios y promociones',
            'Agendamiento_Servicios': 'información sobre nuestros servicios',
            'flujo_agendamiento_servicios': 'información sobre nuestros servicios',
            'Agendamiento_Otra_Consulta': 'consultas generales',
            'flujo_agendamiento_otra_consulta': 'consultas generales',
            'Agendamiento_Tarjeta': 'ventas y afiliación a nuestra tarjeta',
            'flujo_ventas_unisa': 'ventas y afiliación a nuestra tarjeta',
            'CITAS_MP': 'citas por medios propios',
            'flujo_citas_medios_propios': 'citas por medios propios',
            'CITAS_SEGUROS': 'citas con seguro médico',
            'flujo_citas_seguro': 'citas con seguro médico',
            'RESULTADOS_LAB': 'resultados de laboratorio',
            'flujo_resultados_laboratorio': 'resultados de laboratorio',
            'RESULTADOS_IMAGENES': 'resultados de imagenología',
            'flujo_resultados_imagenes': 'resultados de imagenología',
        }
        grupo_texto = descripcion_grupos.get(equipo_asignado, 'atención al cliente')
        pie = []
        if lead_id:
            pie.append(f"📋 **Número de referencia:** {lead_id}")
        if equipo_asignado and grupo_texto:
            pie.append(f"👥 **Área responsable:** {grupo_texto.capitalize()}")
        pie.append("🔒 **Tus datos están protegidos bajo nuestra política de privacidad.**")
        pie.append("📞 **En breve uno de nuestros ejecutivos se comunicará contigo.**")
        pie.append("🙏 **¡Gracias por confiar en UNISA Salud!**")
        return "\n".join(pie)

    @staticmethod
    def generate_response(data, lead_id=None, equipo_asignado=None, env=None):
        """Generar respuesta personalizada según el flujo, usando IA si está disponible."""
        pie = ChatBotUtils._pie_mensaje(lead_id, equipo_asignado)

        # Intentar con IA si está disponible
        descripcion_grupos = {
            'Agendamiento_Directo': 'información general y ubicación',
            'flujo_agendamiento_directo': 'información general y ubicación',
            'Agendamiento_Precios': 'información de precios y promociones',
            'flujo_agendamiento_precios': 'información de precios y promociones',
            'Agendamiento_Servicios': 'información sobre nuestros servicios',
            'flujo_agendamiento_servicios': 'información sobre nuestros servicios',
            'Agendamiento_Otra_Consulta': 'consultas generales',
            'flujo_agendamiento_otra_consulta': 'consultas generales',
            'Agendamiento_Tarjeta': 'ventas y afiliación a nuestra tarjeta',
            'flujo_ventas_unisa': 'ventas y afiliación a nuestra tarjeta',
            'CITAS_MP': 'citas por medios propios',
            'flujo_citas_medios_propios': 'citas por medios propios',
            'CITAS_SEGUROS': 'citas con seguro médico',
            'flujo_citas_seguro': 'citas con seguro médico',
            'RESULTADOS_LAB': 'resultados de laboratorio',
            'flujo_resultados_laboratorio': 'resultados de laboratorio',
            'RESULTADOS_IMAGENES': 'resultados de imagenología',
            'flujo_resultados_imagenes': 'resultados de imagenología',
        }
        grupo_texto = descripcion_grupos.get(equipo_asignado, 'atención al cliente')
        if env and lead_id:
            try:
                service = env.get('gpt.service')
                if service:
                    contexto = {
                        'nombre': data.get('solicitar_name', ''),
                        'lead_id': lead_id,
                        'grupo': grupo_texto,
                        'servicio': data.get('solicitar_servicio', ''),
                        'equipo_asignado': equipo_asignado,
                        'datos_paciente': ChatBotUtils.format_patient_summary(data),
                        'resumen_completo': data,
                    }
                    resultado = service.sudo().generar_mensaje_finalizacion(contexto)
                    if resultado and resultado.get('mensaje_final'):
                        return resultado['mensaje_final'] + "\n\n" + pie
            except Exception:
                _logger.info("IA no disponible para generar respuesta, usando fallback manual")

        # Fallback manual con formato enriquecido
        name = data.get('solicitar_name', '').strip()
        resumen = ChatBotUtils.format_patient_summary(data)
        lines = [f"✅ **¡GRACIAS POR TU SOLICITUD!**"]
        lines.append("")
        lines.append(f"Hemos recibido toda tu información correctamente. {name + ', ' if name else ''}a continuación te compartimos un resumen de lo registrado:\n")
        if resumen:
            lines.append(resumen)
            lines.append("")
        lines.append("📋 **¿Qué sigue?**")
        lines.append("Uno de nuestros asesores revisará tu solicitud y se comunicará contigo en las próximas horas para brindarte la atención que necesitas.")
        lines.append("")
        lines.append(pie)
        return "\n".join(lines)

    @staticmethod
    def format_patient_summary(data):
        """Devuelve un resumen amigable de todos los datos del paciente para mostrar al usuario."""
        lines = []
        
        # Nombre
        name = data.get('solicitar_name') or data.get('name', '')
        if name:
            lines.append(f"👤 **Nombre:** {name}")
        
        # Cédula
        vat = data.get('solicitar_vat') or data.get('vat', '')
        if vat:
            lines.append(f"🆔 **Cédula:** {vat}")
        
        # Teléfono
        phone = data.get('solicitar_phone') or data.get('phone', '')
        if phone:
            lines.append(f"📞 **Teléfono:** {phone}")
        
        # Email
        email = data.get('solicitar_email') or data.get('email', '')
        if email:
            lines.append(f"📧 **Correo:** {email}")
        
        # Fecha de nacimiento
        birthdate = data.get('solicitar_birthdate') or data.get('birthdate', '')
        if birthdate:
            lines.append(f"🎂 **Fecha de nacimiento:** {birthdate}")
        
        # Servicio solicitado
        servicio = data.get('solicitar_servicio') or data.get('servicio_solicitado', '')
        if servicio:
            lines.append(f"🩺 **Servicio solicitado:** {servicio}")
        
        # Consulta deseada
        consulta = data.get('solicitar_consulta_deseada') or data.get('consulta_deseada', '')
        if consulta:
            lines.append(f"💬 **Consulta deseada:** {consulta}")
        
        # Seguro
        seguro = data.get('solicitar_nombre_seguro') or data.get('nombre_seguro', '')
        if seguro:
            lines.append(f"🏥 **Seguro:** {seguro}")
        
        # Fecha y hora preferida
        fecha = data.get('solicitar_fecha_preferida') or data.get('fecha_preferida', '')
        hora = data.get('solicitar_hora_preferida') or data.get('hora_preferida', '')
        if fecha or hora:
            pref = "📅 **Preferencia de cita:** "
            if fecha:
                pref += f"{fecha}"
            else:
                pref += "Lo antes posible"
            if hora:
                pref += f" por la {hora}"
            else:
                pref += " a cualquier hora"
            lines.append(pref)
        
        # Medio de pago
        medio_pago = data.get('solicitar_medio_pago') or data.get('medio_pago', '')
        if medio_pago:
            lines.append(f"💳 **Medio de pago:** {medio_pago}")
        
        # Estudio (para resultados)
        estudio = data.get('estudio_solicitado') or data.get('solicitar_estudio', '')
        if estudio:
            lines.append(f"🔬 **Estudio solicitado:** {estudio}")
        
        if not lines:
            return ""
        
        return "\n".join(lines)

    @staticmethod   
    def validar_valor(valor, tipo_dato, paso=None):
        """Valida un valor según el tipo de dato del paso."""
        if paso == 'solicitar_phone':
            if not valor:
                return False, "El teléfono no puede estar vacío"
            valor_str = str(valor).strip()
            digits = ''.join(filter(str.isdigit, valor_str))
            if not digits:
                return False, "El teléfono debe contener al menos un dígito"
            if len(digits) < 7:
                return False, "El teléfono debe tener al menos 7 dígitos (ej: +584141234567)"
            if len(digits) > 15:
                return False, "El número de teléfono es muy largo. Ingresa un número válido (ej: +584141234567)"
            # Validar que no sea un número inválido (todo ceros, todo el mismo dígito)
            if len(set(digits)) == 1:
                return False, "El número de teléfono no es válido. Ingresa un número real (ej: +584141234567)"
            # Validar que no sean patrones secuenciales obvios
            if digits in ['0123456789', '1234567890', '9876543210']:
                return False, "El número de teléfono no es válido. Ingresa un número real (ej: +584141234567)"
            # Validar prefijo venezolano si parece número local
            if digits.startswith('0') and len(digits) >= 11:
                prefix = digits[1:4]
                prefijos_validos_ve = ['412', '414', '416', '424', '426', '212', '241', '251', '261', '271', '281', '291']
                if prefix not in prefijos_validos_ve:
                    return False, f"El prefijo 0{prefix} no es válido. Ingresa un número venezolano válido (ej: +584141234567)"
            if digits.startswith('58') and len(digits) >= 12:
                prefix = digits[2:5]
                prefijos_validos_ve = ['412', '414', '416', '424', '426', '212', '241', '251', '261', '271', '281', '291']
                if prefix not in prefijos_validos_ve:
                    return False, f"El prefijo {prefix} no es válido. Ingresa un número venezolano válido (ej: +584141234567)"
            return True, valor_str

        if tipo_dato == 'text':
            return True, valor
        elif tipo_dato == 'integer':
            try:
                return True, int(valor)
            except:
                return False, "Debe ser un número entero"
        elif tipo_dato == 'float':
            try:
                return True, float(valor)
            except:
                return False, "Debe ser un número decimal"
        elif tipo_dato == 'date':
            formatos = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%m/%d/%Y']
            valor_str = str(valor).strip()
            for fmt in formatos:
                try:
                    fecha = datetime.strptime(valor_str, fmt).date()
                    return True, fecha.isoformat()
                except ValueError:
                    continue
            return False, "Fecha inválida. Use formato DD/MM/YYYY o YYYY-MM-DD"
        elif tipo_dato == 'datetime':
            try:
                dt = fields.Datetime.from_string(valor)
                return True, dt.isoformat()
            except:
                return False, "Fecha y hora inválida"
        elif tipo_dato == 'boolean':
            if isinstance(valor, bool):
                return True, valor
            if isinstance(valor, str):
                v = valor.lower()
                if v in ['true', '1', 'yes', 'sí', 'si']:
                    return True, True
                elif v in ['false', '0', 'no']:
                    return True, False
            return False, "Debe ser un booleano (sí/no)"
        elif tipo_dato == 'image':
            return True, valor
        elif tipo_dato == 'selection':
            return True, valor
        else:
            return False, f"Tipo de dato no soportado: {tipo_dato}"