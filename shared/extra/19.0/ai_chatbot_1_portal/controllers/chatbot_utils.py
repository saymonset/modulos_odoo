# -*- coding: utf-8 -*-
# Archivo: chatbot_utils.py
from datetime import datetime
import json
import logging
import requests
from odoo import fields, _
import re
import base64

from odoo.addons.ai_chatbot_1_portal.chatbot_prompt_normalizer import (
    normalizar_business_prompt,
    reformatear_prompt_aplanado,
)

_logger = logging.getLogger(__name__)

# Plataformas Meta con límite restringido de caracteres (regla 1A)
META_PLATFORMS = {'instagram', 'messenger', 'facebook', 'meta'}
PLATFORM_LIMITS = {
    'instagram': 900,
    'messenger': 900,
    'facebook': 900,
    'meta': 900,
}
DEFAULT_OUTPUT_LIMIT = 4000   # whatsapp y resto
EMPTY_PLATFORM_LIMIT = 1000   # platform vacío


def truncate_for_platform(text, platform):
    """Recorta un mensaje para no exceder el límite de la plataforma.

    Solo recorta si hace falta; si el texto ya cabe, devuelve el original.
    Aplica un límite conservador (menor al tope de la API) para que el envío
    nunca falle por longitud en Instagram/Messenger/Facebook/Meta.
    """
    if not text:
        return text
    pdf = platform.lower() if platform else ''
    if pdf in META_PLATFORMS:
        limit = PLATFORM_LIMITS['instagram']
    elif pdf:
        limit = DEFAULT_OUTPUT_LIMIT
    else:
        limit = EMPTY_PLATFORM_LIMIT
    if len(text) <= limit:
        return text
    truncated = text[:limit - 3]  # reserva espacio para "..."
    cut = truncated.rfind(' ')
    if cut > 0:
        truncated = truncated[:cut]
    return truncated.rstrip() + '...'


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
    def get_or_create_crm_teams(env):
        """Obtener o crear equipos CRM (Grupo Citas, Grupo Ventas, Grupo Laboratorio, Grupo Imagenología, Grupo Informativo)"""
        teams = {}
        team_names = ['Grupo Citas', 'Grupo Ventas', 'Grupo Laboratorio', 'Grupo Imagenología', 'Grupo Informativo']
        for team_name in team_names:
            # Buscar con entorno sudo y contexto en_US porque name es translate=True y puede no tener es_VE
            team = env['crm.team'].sudo().with_context(lang='en_US').search([('name', '=', team_name)], limit=1)
            if not team:
                try:
                    team_data = {
                        'name': team_name,
                        'active': True,
                    }
                    if team_name == 'Grupo Citas':
                        team_data['alias_name'] = 'citas'
                    elif team_name == 'Grupo Ventas':
                        team_data['alias_name'] = 'ventas'
                    elif team_name == 'Grupo Laboratorio':
                        team_data['alias_name'] = 'laboratorio'
                    elif team_name == 'Grupo Imagenología':
                        team_data['alias_name'] = 'imagenologia'
                    elif team_name == 'Grupo Informativo':
                        team_data['alias_name'] = 'informativo'
                    team = env['crm.team'].create(team_data)
                    _logger.info(f"✅ Equipo CRM creado: {team.name} (ID: {team.id})")
                except Exception as e:
                    _logger.error(f"❌ Error creando equipo {team_name}: {str(e)}")
                    # Posible condición de carrera: reintentar buscar si otro proceso creó el equipo
                    team = env['crm.team'].sudo().with_context(lang='en_US').search([('name', '=', team_name)], limit=1)
                    if not team:
                        # Como último recurso, crear un equipo con sufijo para evitar bloqueos por duplicado
                        try:
                            team = env['crm.team'].create({'name': team_name + ' (Fallback)', 'active': True})
                            _logger.warning(f"⚠️ Se creó equipo genérico: {team.name}")
                        except Exception as e2:
                            _logger.error(f"❌ No se pudo crear equipo fallback para {team_name}: {e2}")
                            team = env['crm.team'].search([], limit=1)
            else:
                _logger.info(f"✅ Equipo CRM encontrado: {team.name} (ID: {team.id})")
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
        source_name = f"{platform_display} Bot IntegraIA"
        source = env['utm.source'].search([('name', '=ilike', source_name)], limit=1)
        if not source:
            source = env['utm.source'].create({'name': source_name})
        campaign_name = f"Campaña {platform_display} IntegraIA"
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
        descripcion_grupos = env['chatbot.flujo']._get_mapeo_equipo_descripcion()
        area_texto = descripcion_grupos.get(equipo_asignado, '')
        if area_texto:
            description += f"\n\n**👥 CENTRAL DE CITAS:** {area_texto.capitalize()}"
        if team:
            description += f"\n**🏥 EQUIPO ASIGNADO:** {team.name}"
        
        # Normalizar teléfono para lead
        phone_raw = data.get('phone') or data.get('solicitar_phone', '')
        phone_normalizado = ChatBotUtils.normalizar_telefono_internacional(phone_raw)
        # Para el lead, mostrar sin +58 (para WhatsApp local)
        phone_lead = phone_normalizado.replace('+58', '') if phone_normalizado.startswith('+58') else phone_normalizado
        email = data.get('email') or data.get('solicitar_email') or partner.email or ''
        
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
            (('solicitar_name', 'name'), 'Cliente'),
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
            (('solicitar_es_paciente_nuevo', 'es_paciente_nuevo'), 'Cliente nuevo'),
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

        # Campos personalizados del flujo: se agregan automáticamente.
        # De este modo cualquier paso con campo_destino propio (producto,
        # material, cantidad, dedicatoria, etc.) queda visible en el lead.
        claves_conocidas = set()
        for keys, _label in fields_order:
            claves_conocidas.update(keys)
        claves_internas = {
            'account_id', 'conversation_id', 'session_id', 'equipo_asignado',
            'flow_name', 'name_flow', 'consentimiento', 'plataforma',
            'informacion_precios',
        }
        for clave, valor in data.items():
            if clave in claves_conocidas or clave in claves_internas:
                continue
            if valor is None or valor == '' or valor is False:
                continue
            if isinstance(valor, (list, dict)):
                if not valor:
                    continue
                valor = json.dumps(valor, ensure_ascii=False, default=str)
            etiqueta = clave.replace('solicitar_', '').replace('_', ' ').strip()
            etiqueta = etiqueta.capitalize()
            lines.append(f"• {etiqueta}: {valor}")

        return "\n".join(lines)

    @staticmethod
    def build_agent_system_prompt(env):
        """
        Construye el system prompt que n8n inyecta al Agente_Informacion_basica.

        Combina:
        1. Mensaje de negocio configurado en Ajustes.
        2. Catálogo de flujos activos (nombre, routing_key, política, reglas).
        3. Reglas técnicas fijas de formato de salida.

        No contiene información fija de ninguna industria: se genera
        dinámicamente a partir de la configuración de Odoo.
        """
        params = env['ir.config_parameter'].sudo()
        business_prompt = params.get_param('ai_chatbot_1_portal.system_prompt', '') or ''
        business_prompt, _n = reformatear_prompt_aplanado(business_prompt)
        business_prompt, _n = normalizar_business_prompt(business_prompt)

        flujos = env['chatbot.flujo'].sudo().search([('active', '=', True)], order='name')

        lines = []
        lines.append('=== INFORMACIÓN DEL NEGOCIO ===')
        lines.append(business_prompt.strip() if business_prompt.strip() else
                     '(Sin información comercial configurada)')
        lines.append('')

        if flujos:
            lines.append('=== FLUJOS DISPONIBLES (usa EXACTAMENTE estos valores) ===')
            for i, flujo in enumerate(flujos, 1):
                routing_key = flujo.routing_key or flujo.name
                politica_texto = dict(flujo._fields['politica_inicio'].selection).get(
                    flujo.politica_inicio, flujo.politica_inicio)
                lines.append(f"{i}. flow_name: {flujo.name}")
                lines.append(f"   - equipo_asignado (código de enrutamiento): {routing_key}")
                lines.append(f"   - Política de inicio: {politica_texto}")
                if flujo.descripcion_intencion:
                    lines.append(f"   - Activar cuando: {flujo.descripcion_intencion.strip()}")
                if flujo.condiciones_no_inicio:
                    lines.append(f"   - NO activar cuando: {flujo.condiciones_no_inicio.strip()}")
            lines.append('')
        else:
            lines.append('(No hay flujos activos configurados.)')
            lines.append('')

        lines.append('=== FORMATO DE SALIDA OBLIGATORIO ===')
        lines.append('Responde SIEMPRE y ÚNICAMENTE con un objeto JSON válido:')
        lines.append('{')
        lines.append('  "output": "",')
        lines.append('  "tipoPregunta": "",')
        lines.append('  "isMenu": false,')
        lines.append('  "equipo_asignado": "",')
        lines.append('  "flow_name": "",')
        lines.append('  "session_id": "",')
        lines.append('  "conversation_id": "",')
        lines.append('  "account_id": "",')
        lines.append('  "platform": "",')
        lines.append('  "timestamp_actividad": ""')
        lines.append('}')
        lines.append('')
        lines.append('REGLAS:')
        lines.append('1. "flow_name" debe ser EXACTAMENTE el nombre de un flujo disponible de la lista.')
        lines.append('   "equipo_asignado" debe ser el código de enrutamiento de ese mismo flujo.')
        lines.append(f'2. Si el usuario hace una consulta informativa (precios, servicios, '
                     f'horarios, promociones) NO inicies aún un flujo de captura: devuelve '
                     f'equipo_asignado="" y flow_name="".')
        lines.append(f'3. Solo activa un flujo cuando el usuario confirme que desea dejar sus '
                     f'datos, realizar un pedido, agendar una cita o derivar al equipo humano.')
        lines.append('4. Si no hay un flujo que corresponde, usa flow_name vacío.')
        lines.append('5. Copia session_id, conversation_id, account_id, platform y timestamp_actividad del input.')
        lines.append('6. Límite de caracteres: 4000 para WhatsApp, 900 para redes (instagram/facebook/messenger).')
        lines.append('   Si el prompt tiene "VERSIÓN CORTA OBLIGATORIA", úsala exactamente cuando platform sea '
                     'instagram/messenger/facebook/meta.')
        lines.append('   Como seguridad adicional Odoo recorta cualquier output que supere el límite de la plataforma.')
        lines.append('7. Envía el JSON sin markdown, sin texto adicional y sin comentarios.')
        lines.append('')
        return '\n'.join(lines)

    @staticmethod
    def get_default_stage(env):
        """Obtener etapa por defecto para leads"""
        stage = env['crm.stage'].search([('name', 'ilike', 'nuevo')], limit=1)
        if not stage:
            stage = env['crm.stage'].search([], limit=1)
        return stage.id if stage else False

    @staticmethod
    def assign_lead_round_robin(env, lead, team):
        """Asignar lead usando round robin y enviar email al asignado"""
        _logger.info('RR[Odoo] INICIO: lead_id=%s team=%s(%s)', lead.id, team.name if team else None, team.id if team else None)
        if not team or not team.member_ids:
            _logger.warning('RR[Odoo] SKIP: team=%s member_ids=%s', team.name if team else None, team.member_ids.ids if team and team.member_ids else 'vacio')
            return
        try:
            param_name = f'chatbot_last_user_{team.id}'
            last_assigned_user_id = env['ir.config_parameter'].sudo().get_param(param_name)
            team_members = team.member_ids.sorted('id')
            _logger.info('RR[Odoo] team=%s members_count=%s members_ids=%s',
                         team.name, len(team_members), team_members.ids)
            _logger.info('RR[Odoo] last_assigned_user_id=%s (param=%s)', last_assigned_user_id, param_name)
            if last_assigned_user_id:
                last_user = env['res.users'].browse(int(last_assigned_user_id))
                _logger.info('RR[Odoo] last_user: id=%s name=%s in_team=%s',
                             last_user.id, last_user.name, last_user in team_members)
                if last_user in team_members:
                    current_index = team_members.ids.index(last_user.id)
                    next_index = (current_index + 1) % len(team_members)
                    next_user = team_members[next_index]
                    _logger.info('RR[Odoo] rotando: last_index=%d next_index=%d', current_index, next_index)
                else:
                    next_user = team_members[0]
                    _logger.info('RR[Odoo] last_user no está en team, usando primero')
            else:
                next_user = team_members[0]
                _logger.info('RR[Odoo] sin last_assigned, usando primer miembro del team')
            _logger.info('RR[Odoo] ASIGNADO: user_id=%s name=%s email=%s',
                         next_user.id, next_user.name, next_user.partner_id.email)
            lead.write({'user_id': next_user.id})
            env['ir.config_parameter'].sudo().set_param(param_name, next_user.id)
            _logger.info(f"RR[Odoo] Lead {lead.id} asignado a {next_user.name} (ID {next_user.id})")
            ChatBotUtils._send_assignment_email(env, lead, next_user)
            _logger.info('RR[Odoo] FIN OK')
        except Exception as e:
            _logger.warning(f"RR[Odoo] Error en round robin: {str(e)}", exc_info=True)

    @staticmethod
    def _send_assignment_email(env, lead, user):
        """Enviar email de notificación al usuario asignado"""
        if not user.partner_id.email:
            _logger.warning(f"Usuario {user.name} no tiene email, no se envía notificación")
            return
        try:
            subject = f"Nuevo lead asignado: {lead.name}"
            servicio = lead.name.split(' - ')[0] if ' - ' in lead.name else lead.name
            body = (
                f"<p>Hola {user.name},</p>"
                f"<p>Se te ha asignado un nuevo lead generado desde el chatbot de IntegraIA.</p>"
                f"<br/>"
                f"<p><strong>Datos del cliente:</strong></p>"
                f"<ul>"
                f"<li><strong>Nombre:</strong> {lead.contact_name or ''}</li>"
                f"<li><strong>Teléfono:</strong> {lead.phone or ''}</li>"
                f"<li><strong>Email:</strong> {lead.email_from or ''}</li>"
                f"<li><strong>Servicio:</strong> {servicio}</li>"
                f"<li><strong>Equipo:</strong> {lead.team_id.name or 'Sin equipo'}</li>"
                f"</ul>"
                f"<p>Por favor, contacta al cliente a la brevedad para dar seguimiento a su solicitud.</p>"
                f"<p>Saludos,<br/><strong>Sistema IntegraIA</strong></p>"
            )
            email_from = env['ir.config_parameter'].sudo().get_param('mail.default.from', 'admin@integraiaconodoo.com')
            env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body,
                'email_to': user.partner_id.email,
                'email_from': email_from,
                'model': 'crm.lead',
                'res_id': lead.id,
            })
            _logger.info(f"Email de notificación creado para {user.name} ({user.partner_id.email}) por lead {lead.id}")
        except Exception as e:
            _logger.warning(f"Error creando email de asignación: {str(e)}")

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
    def _get_brand_name(env):
        """Devuelve el nombre de marca configurado en Ajustes, o el de la compañía,
        o un fallback genérico."""
        if env:
            params = env['ir.config_parameter'].sudo()
            brand = params.get_param('ai_chatbot_1_portal.brand_name') or ''
            if not brand:
                brand = env.company.name or ''
            if brand:
                return brand
        return 'IntegraIA'

    @staticmethod
    def _platform_attribution_line(env):
        """Línea promocional de la plataforma (cursiva, sutil).

        Solo aparece si el parámetro ai_chatbot_1_portal.platform_promotion_enabled
        está activo. El texto se configura en ai_chatbot_1_portal.platform_promotion_text.
        """
        if not env:
            return ""
        params = env['ir.config_parameter'].sudo()
        enabled = params.get_param('ai_chatbot_1_portal.platform_promotion_enabled')
        if not enabled or str(enabled).lower() not in ('1', 'true', 'yes', 'on'):
            return ""
        text = params.get_param('ai_chatbot_1_portal.platform_promotion_text') or '@integraiaconodoo'
        return f"\n\n_Atención automatizada por {text}_"

    @staticmethod
    def _pie_mensaje(lead_id, equipo_asignado, env=None):
        """Genera el pie del mensaje con datos de referencia (formato neutro)."""
        pie = []
        if lead_id:
            pie.append(f"Referencia: {lead_id}")
        if env and equipo_asignado:
            desc = env['chatbot.flujo']._get_mapeo_equipo_descripcion()
            tema = desc.get(equipo_asignado, '')
            if tema:
                pie.append(f"📌 {tema.capitalize()}")
        pie.append("Proceso: Asignación y seguimiento de solicitud.")
        pie.append("Privacidad: Tus datos cuentan con total confidencialidad.")
        pie.append("Siguiente paso: Nuestro equipo se comunicará en breve.")
        pie.append(f"Agradecimiento: Gracias por elegir a {ChatBotUtils._get_brand_name(env)}.")
        pie.append(ChatBotUtils._platform_attribution_line(env))
        return "\n".join(line for line in pie if line)

    @staticmethod
    def _build_flow_audit(env, name_flow, data):
        """
        Auditoría técnica de la ejecución del flujo para personal interno.

        Compara los pasos preconfigurados del flujo (chatbot.paso) con los
        datos realmente recolectados (data) y devuelve un dict JSON-serializable
        con los pasos esperados vs completados y el estado general del flujo.

        Si no se encuentra el flujo o no tiene pasos, devuelve un dict mínimo
        sin falsear el resultado (flow_ok=None indica "sin información").
        """
        audit = {
            'flow_name': name_flow,
            'flow_ok': None,
            'steps_expected': [],
            'steps_completed': [],
            'steps_missing': [],
        }
        flujo = None
        if name_flow:
            flujo = env['chatbot.flujo'].sudo().search([('name', '=', name_flow)], limit=1)
        if not flujo or not flujo.paso_ids:
            _logger.warning('audit: flujo %s no encontrado o sin pasos', name_flow)
            return audit

        data_values = data or {}
        for paso in flujo.paso_ids.sorted('secuencia'):
            if not paso.active:
                continue
            campo = paso.campo_destino
            audit['steps_expected'].append({
                'nombre': paso.nombre_mostrar or campo,
                'campo_destino': campo,
                'es_requerido': paso.es_requerido,
            })
            valor = ChatBotUtils._get_step_value(data_values, campo)
            if valor is not None and valor != '':
                audit['steps_completed'].append(campo)
            else:
                audit['steps_missing'].append({
                    'nombre': paso.nombre_mostrar or campo,
                    'campo_destino': campo,
                    'es_requerido': paso.es_requerido,
                })

        requeridos_pendientes = [s for s in audit['steps_missing'] if s['es_requerido']]
        audit['flow_ok'] = not requeridos_pendientes
        return audit

    @staticmethod
    def _get_step_value(data_values, campo_destino):
        """
        Resuelve el valor de un campo_destino en el dict de datos.

        n8n puede enviar el valor con o sin el prefijo 'solicitar_',
        y existen alias por convención de cada flujo.
        """
        alias = {
            'telefono': ['phone', 'solicitar_phone', 'telefono'],
            'phone': ['phone', 'solicitar_phone', 'telefono'],
            'nombre_completo': ['name', 'solicitar_name', 'nombre_completo'],
            'name': ['name', 'solicitar_name', 'nombre_completo'],
            'consentimiento_whatsapp': ['consentimiento', 'consentimiento_whatsapp'],
            'identificacion_paciente': ['identificacion_paciente', 'solicitar_identificacion', 'solicitar_name', 'name'],
            'estudio_solicitado': ['estudio_solicitado', 'solicitar_estudio', 'solicitar_servicio', 'servicio_solicitado'],
        }
        candidatos = alias.get(campo_destino) or (
            [campo_destino]
            + [f'solicitar_{campo_destino}']
            + [f'solicitar_{campo_destino.replace("solicitar_", "")}']
        )
        for key in candidatos:
            if key in data_values:
                return data_values.get(key)
        return None

    @staticmethod
    def _build_notify_message_with_audit(mapping_rec, assigned_agent_email, audit):
        """
        Mensaje de notificación interna para el agente Chatwoot.

        Incluye la referencia del flujo y el estado de cumplimiento de pasos
        (completados vs esperados) para que el personal técnico pueda auditar
        si el flujo se comportó correctamente.
        """
        equipo = (mapping_rec.equipo_asignado or '').replace('_', ' ')
        lines = [f"Tu consulta sobre {equipo} ha sido registrada."]
        if assigned_agent_email:
            lines.append(f"Agente asignado: {assigned_agent_email}")

        if audit and audit.get('flow_name'):
            lines.append("")
            lines.append(f"Flujo: {audit.get('flow_name')}")
            if audit.get('flow_ok') is not None:
                estado = 'COMPLETADO' if audit['flow_ok'] else 'INCOMPLETO'
                lines.append(f"Estado: {estado}")
            completados = set(audit.get('steps_completed', []))
            lineas_pasos = []
            for paso in audit.get('steps_expected', []):
                campo = paso.get('campo_destino')
                marca = '✓' if campo in completados else '✗'
                lineas_pasos.append(f"{marca} {paso.get('nombre')}")
            lines.append("Pasos: " + " | ".join(lineas_pasos))
        return "\n".join(lines)

    @staticmethod
    def generate_response(data, lead_id=None, equipo_asignado=None, env=None):
        """Generar respuesta personalizada según el flujo, usando IA si está disponible."""
        pie = ChatBotUtils._pie_mensaje(lead_id, equipo_asignado, env=env)

        descripcion_grupos = env['chatbot.flujo']._get_mapeo_equipo_descripcion() if env else {}
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
                        return truncate_for_platform(
                            resultado['mensaje_final'] + "\n\n" + pie,
                            data.get('platform'),
                        )
            except Exception:
                _logger.info("IA no disponible para generar respuesta, usando fallback manual")

        # Fallback manual con formato neutro
        name = data.get('solicitar_name', '').strip()
        resumen = ChatBotUtils.format_patient_summary(data)
        lines = ["Confirmación: Hemos recibido tu información correctamente."]
        lines.append("")
        if name:
            lines.append(f"{name}, a continuación un resumen de lo registrado:")
        else:
            lines.append("A continuación, un resumen de lo registrado:")
        lines.append("")
        if resumen:
            lines.append(resumen)
            lines.append("")
        lines.append("Siguiente paso: Nuestro equipo revisará tu solicitud y se comunicará contigo en las próximas horas.")
        lines.append("")
        lines.append(pie)
        return truncate_for_platform("\n".join(lines), data.get('platform'))

    @staticmethod
    def format_patient_summary(data):
        """Devuelve un resumen neutro de todos los datos del cliente para mostrar al usuario."""
        lines = []
        
        # Nombre
        name = data.get('solicitar_name') or data.get('name', '')
        if name:
            lines.append(f"Nombre: {name}")
        
        # Cédula
        vat = data.get('solicitar_vat') or data.get('vat', '')
        if vat:
            lines.append(f"Cédula: {vat}")
        
        # Teléfono
        phone = data.get('solicitar_phone') or data.get('phone', '')
        if phone:
            lines.append(f"Teléfono: {phone}")
        
        # Email
        email = data.get('solicitar_email') or data.get('email', '')
        if email:
            lines.append(f"Correo: {email}")
        
        # Fecha de nacimiento
        birthdate = data.get('solicitar_birthdate') or data.get('birthdate', '')
        if birthdate:
            lines.append(f"Fecha de nacimiento: {birthdate}")
        
        # Servicio solicitado
        servicio = data.get('solicitar_servicio') or data.get('servicio_solicitado', '')
        if servicio:
            lines.append(f"Servicio solicitado: {servicio}")
        
        # Consulta deseada
        consulta = data.get('solicitar_consulta_deseada') or data.get('consulta_deseada', '')
        if consulta:
            lines.append(f"Consulta: {consulta}")
        
        # Seguro
        seguro = data.get('solicitar_nombre_seguro') or data.get('nombre_seguro', '')
        if seguro:
            lines.append(f"Seguro: {seguro}")
        
        # Fecha y hora preferida
        fecha = data.get('solicitar_fecha_preferida') or data.get('fecha_preferida', '')
        hora = data.get('solicitar_hora_preferida') or data.get('hora_preferida', '')
        if fecha or hora:
            pref = "Preferencia: "
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
            lines.append(f"Medio de pago: {medio_pago}")
        
        # Estudio (para resultados)
        estudio = data.get('estudio_solicitado') or data.get('solicitar_estudio', '')
        if estudio:
            lines.append(f"Estudio solicitado: {estudio}")
        
        if not lines:
            return ""
        
        return "\n".join(lines)

    @staticmethod
    def _is_image_url(url, timeout=2):
        """Comprueba de forma ligera si la URL parece una imagen.
        Retorna (True, url) si pasa; (False, motivo) si no."""
        if not url or not isinstance(url, str):
            return False, "URL inválida"
        url = url.strip()
        if not re.match(r'^https?://', url, re.IGNORECASE):
            return False, "La URL debe comenzar con http(s)://"
        lower = url.lower()
        image_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg', '.tiff')
        if any(lower.endswith(ext) for ext in image_exts):
            return True, url
        try:
            resp = requests.head(url, allow_redirects=True, timeout=timeout)
            ctype = resp.headers.get('Content-Type', '').lower()
            if ctype.startswith('image/'):
                return True, url
            return False, f"Content-Type no indica imagen: {ctype or 'desconocido'}"
        except requests.exceptions.RequestException as e:
            return False, f"No se pudo verificar la URL (HEAD): {str(e)}"

    @staticmethod   
    def validar_valor(valor, tipo_dato, paso=None):
        """Valida un valor según el tipo de dato del paso."""
        if paso in ('solicitar_phone', 'phone', 'telefono'):
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
            ok, info = ChatBotUtils._is_image_url(valor)
            if ok:
                return True, valor
            return False, f"No se detectó imagen válida: {info}. Reenvía la foto o escribe 'saltar' para omitir."
        elif tipo_dato == 'selection':
            return True, valor
        else:
            return False, f"Tipo de dato no soportado: {tipo_dato}"
