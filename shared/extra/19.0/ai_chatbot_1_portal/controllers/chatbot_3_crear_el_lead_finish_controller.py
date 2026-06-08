from odoo import http
from odoo.http import request, Response
import json
import logging
import re
from datetime import datetime

from .chatbot_utils import ChatBotUtils

_logger = logging.getLogger(__name__)


class ChatBotController(http.Controller):
    
    @http.route('/ai_chatbot_1_portal/buscar_por_telefono_http',
                auth='public',
                type='http',
                methods=['POST'],
                csrf=False,
                cors='*')
    def buscar_por_telefono_http(self, **kw):
        """
        Búsqueda rápida solo por teléfono para iniciar conversación
        Versión optimizada usando ChatBotUtils
        """
        try:
            _logger.info("=== INICIO BUSQUEDA POR TELEFONO HTTP (OPTIMIZADO) ===")
            
            http_request = request.httprequest
            content_type = http_request.headers.get('Content-Type', '').lower()
            data = {}
            
            if 'application/json' in content_type:
                try:
                    if http_request.data:
                        raw_data = http_request.get_data(as_text=True)
                        if raw_data.strip():
                            data = json.loads(raw_data)
                except json.JSONDecodeError as e:
                    _logger.error("Error decodificando JSON: %s", str(e))
                    return Response(
                        json.dumps({'error': True, 'mensaje': 'Formato JSON inválido', 'detalle': str(e)}),
                        status=400,
                        content_type='application/json; charset=utf-8',
                        headers=[('Access-Control-Allow-Origin', '*')]
                    )
            else:
                data = dict(http_request.form)
                if not data:
                    data = dict(http_request.args)
            
            telefono = (data.get('solicitar_phone') or '')
            if not telefono:
                _logger.warning("No se proporcionó teléfono en la petición")
                return Response(
                    json.dumps({'existe': False, 'error': True, 'mensaje': 'Parámetro "solicitar_phone" es requerido'}),
                    content_type='application/json; charset=utf-8',
                    headers=[('Access-Control-Allow-Origin', '*')]
                )
            
            # 🔧 NORMALIZAR TELÉFONO ANTES DE BUSCAR
            telefono_normalizado = ChatBotUtils.normalizar_telefono_internacional(telefono)
            _logger.info("Buscando cliente con teléfono original: %s - Normalizado: %s", telefono, telefono_normalizado)
            
            try:
                admin_uid = request.env.ref('base.user_admin').id or 2
            except Exception:
                admin_uid = 2
                
            env = request.env(user=admin_uid)
            search_data = {'telefono': telefono_normalizado}  # Usamos el teléfono normalizado
            partner = ChatBotUtils.search_contact(env, search_data)
            
            if partner and partner.id and partner.name and partner.name != 'Sin nombre':
                _logger.info("Cliente encontrado: %s (ID: %s)", partner.name, partner.id)
                ultima_cita_info = ChatBotUtils.get_ultima_cita(env, partner.id)
                ultima_cita_str = ""
                if ultima_cita_info:
                    ultima_cita_str = f"{ultima_cita_info.get('fecha', '')} - {ultima_cita_info.get('servicio', '')}"
                fecha_nac_formateada = ''
                if partner.birthdate:
                    try:
                        fecha_nac_formateada = partner.birthdate.strftime('%d/%m/%Y')
                    except Exception:
                        fecha_nac_formateada = str(partner.birthdate)
                
                response_data = {
                    'existe': True,
                    'iniciales': self._get_iniciales(partner.name),
                    'mensaje': f"✅ **INFORMACIÓN ENCONTRADA**\n\n"
                               f"👤 **Datos del paciente:**\n"
                               f"• Nombre: {partner.name}\n"
                               f"• Cédula: {partner.vat or 'No registrada'}\n"
                               f"• Teléfono: {partner.phone}\n",
                    'ultima_cita': ultima_cita_str,
                    'cedula': partner.vat or '',
                    'nombre_completo': partner.name or '',
                    'fecha_nacimiento': fecha_nac_formateada,
                    'telefono': partner.phone or '',
                    'email': partner.email or '',
                    'es_paciente_nuevo': 'no',
                    'id_cliente': partner.id,
                    'pais': partner.country_id.name if partner.country_id else '',
                    'ciudad': partner.city or '',
                    'detalle_ultima_cita': ultima_cita_info or {}
                }
                return Response(
                    json.dumps(response_data, default=str),
                    content_type='application/json; charset=utf-8',
                    headers=[('Access-Control-Allow-Origin', '*')]
                )
            
            _logger.info("Cliente NO encontrado para teléfono: %s (normalizado: %s)", telefono, telefono_normalizado)
            mensaje = "❌ **NO ENCONTRAMOS TU REGISTRO**\n\nNo encontramos información con ese número de teléfono.\n\n📋 **Por favor, ingresa tu cédula (solo números):**\n\nEjemplo: 12345678"
            return Response(
                json.dumps({'existe': False, 'mensaje': mensaje, 'telefono_buscado': telefono, 'sugerencia': 'Puede ser un nuevo cliente o el teléfono no está registrado'}),
                content_type='application/json; charset=utf-8',
                headers=[('Access-Control-Allow-Origin', '*')]
            )
        except Exception as e:
            _logger.error("ERROR CRÍTICO BUSCANDO POR TELÉFONO: %s", str(e), exc_info=True)
            return Response(
                json.dumps({'existe': False, 'error': True, 'mensaje': 'Error interno del servidor', 'tipo_error': type(e).__name__}),
                status=500,
                content_type='application/json; charset=utf-8',
                headers=[('Access-Control-Allow-Origin', '*')]
            )
    
    def _get_iniciales(self, nombre_completo):
        """Obtiene las iniciales del nombre (mantenido para compatibilidad)"""
        if not nombre_completo:
            return ''
        try:
            partes = nombre_completo.split()
            iniciales = ''.join([parte[0].upper() for parte in partes[:2] if parte])
            return iniciales    
        except Exception:
            return nombre_completo[:2].upper() if len(nombre_completo) >= 2 else nombre_completo[0].upper()
    
    @http.route('/ai_chatbot_1_portal/capturar_lead_http',
                auth='public',
                type='http',
                methods=['POST'],
                csrf=False,
                cors='*')
    def capturar_lead_http(self, **kw):
        """
        Crear cita completa usando ChatBotUtils
        Versión optimizada
        """
        try:
            _logger.info("=== INICIO CREACION DE CITA HTTP (OPTIMIZADO) ===")
            
            http_request = request.httprequest
            content_type = http_request.headers.get('Content-Type', '').lower()
            data = {}
            
            if 'application/json' in content_type:
                try:
                    if http_request.data:
                        raw_data = http_request.get_data(as_text=True)
                        if raw_data.strip():
                            data = json.loads(raw_data)
                except json.JSONDecodeError as e:
                    return Response(
                        json.dumps({'error': True, 'mensaje': 'JSON inválido'}),
                        status=400,
                        content_type='application/json; charset=utf-8'
                    )
            else:
                data = dict(http_request.form)
                if not data:
                    data = dict(http_request.args)
            
            _logger.info("Datos recibidos para crear cita: %s", json.dumps(data, default=str))
            _logger.info("Email recibido: %s", data.get('solicitar_email'))
            _logger.info("Consentimiento recibido: %s", data.get('consentimiento'))
            
            # Validar datos requeridos
            campos_requeridos = ['solicitar_vat', 'solicitar_phone', 'solicitar_name', 'solicitar_birthdate']
            for campo in campos_requeridos:
                if campo not in data or not data[campo]:
                    return Response(
                        json.dumps({'error': True, 'mensaje': f'Campo requerido faltante: {campo}'}),
                        content_type='application/json; charset=utf-8'
                    )
            
            try:
                admin_uid = request.env.ref('base.user_admin').id or 2
            except Exception:
                admin_uid = 2
            env = request.env(user=admin_uid)
            
            # Crear o actualizar contacto (ya incluye email y consentimiento)
            partner = ChatBotUtils.update_create_contact(env, {
                'solicitar_vat': data.get('solicitar_vat', ''),
                'solicitar_phone': data.get('solicitar_phone', ''),
                'solicitar_name': data.get('solicitar_name', ''),
                'solicitar_birthdate': data.get('solicitar_birthdate', ''),
                'solicitar_email': data.get('solicitar_email', ''),
                'consentimiento': data.get('consentimiento', False)
            })
            
            # Configurar UTM y etiquetas
            plataforma = data.get('plataforma', 'whatsapp')
            medium, source, campaign = ChatBotUtils.setup_utm(env, plataforma)
            tag = ChatBotUtils.get_or_create_bot_tag(env, plataforma)
            teams = ChatBotUtils.get_team_unisa(env)
            
            equipo_asignado = data.get('equipo_asignado', 'Agendamiento_Directo')
            # Intentar obtener el flujo por name_flow y usar su team_id si está configurado
            nombre_grupo = None
            team = None
            name_flow = data.get('name_flow') or data.get('flow_name') or None
            if name_flow:
                flujo = env['chatbot.flujo'].search([('name', '=', name_flow)], limit=1)
                if flujo and flujo.team_id:
                    team = flujo.team_id
                    nombre_grupo = team.name
            # Si no encontramos equipo por el flujo, usar el mapeo central
            if not team:
                mapeo_grupos = env['chatbot.flujo']._get_mapeo_equipo_grupo()
                nombre_grupo = mapeo_grupos.get(equipo_asignado)
                if nombre_grupo:
                    if teams and nombre_grupo in teams:
                        team = teams.get(nombre_grupo)
                    else:
                        team = env['crm.team'].sudo().search([('name', '=', nombre_grupo)], limit=1)
                        if not team:
                            team = env['crm.team'].sudo().search([], limit=1)
                            _logger.warning(f"No se encontró el equipo {nombre_grupo}, usando {team.name if team else 'ninguno'}")
            
            _logger.info(f"Equipo asignado: {equipo_asignado} -> Grupo: {nombre_grupo or 'Sin grupo'} -> ID: {team.id if team else 'N/A'}")
            
            # Crear lead según el tipo de flujo
            if equipo_asignado in ['RESULTADOS_LAB', 'RESULTADOS_IMAGENES', 'flujo_resultados_laboratorio', 'flujo_resultados_imagenes']:
                lead = ChatBotUtils.create_resultados_lead(env, data, team, medium, source, campaign, tag)
            else:
                lead = ChatBotUtils.create_lead(env, data, partner, team, medium, source, campaign, tag)
            
            # Asignación round robin
            team_sudo = team.sudo() if team else None
            if team_sudo and team_sudo.member_ids:
                ChatBotUtils.assign_lead_round_robin(env, lead, team_sudo)
            
            # Manejar imágenes
            if data.get('solicitar_foto_vat') or data.get('foto_vat') or data.get('solicitar_imagenes_adicionales') or data.get('imagenes_adicionales'):
                validated_images = ChatBotUtils.validate_image_urls(data)
                data.update(validated_images)
                ChatBotUtils.handle_images(env, data, lead, partner)

            # Asignación Chatwoot (round-robin + notify)
            account_id_cw = data.get('account_id')
            conversation_id_cw = data.get('conversation_id')
            _logger.info('RR[HTTP] INICIO bloque Chatwoot: account=%s conv=%s team=%s equipo=%s flow=%s',
                         account_id_cw, conversation_id_cw,
                         team.name if team else None, equipo_asignado, name_flow)
            if account_id_cw and conversation_id_cw:
                try:
                    _logger.info('RR[HTTP] llamando select_round_robin_mapping con team=%s(%s) equipo=%s flow=%s',
                                 team.name if team else None, team.id if team else None, equipo_asignado, name_flow)
                    mapping_rec = env['chatwoot.mapping'].sudo().select_round_robin_mapping(
                        team=team,
                        equipo_asignado=equipo_asignado,
                        flow_name=name_flow,
                    )
                    if mapping_rec:
                        _logger.info('RR[HTTP] mapping SELECCIONADO: id=%s name=%s agent_id=%s agent_email=%s inbox_id=%s tags=%s',
                                     mapping_rec.id, mapping_rec.name,
                                     mapping_rec.chatwoot_agent_id, mapping_rec.chatwoot_agent_email,
                                     mapping_rec.chatwoot_inbox_id, mapping_rec.chatwoot_tags)
                    else:
                        _logger.warning('RR[HTTP] NO SE ENCONTRÓ MAPPING - team=%s equipo=%s flow=%s',
                                        team.name if team else None, equipo_asignado, name_flow)

                    if mapping_rec:
                        _logger.info('RR[HTTP] consultando get_agent_details account=%s agent_id=%s agent_email=%s',
                                     account_id_cw, mapping_rec.chatwoot_agent_id, mapping_rec.chatwoot_agent_email)
                        agent_details = env['chatwoot.client'].get_agent_details(
                            account_id_cw,
                            agent_id=mapping_rec.chatwoot_agent_id or None,
                            agent_email=mapping_rec.chatwoot_agent_email or None,
                        )
                        _logger.info('RR[HTTP] agent_details RESULTADO: %s', agent_details)
                        assigned_agent_name = None
                        assigned_agent_email = None
                        if agent_details:
                            assigned_agent_name = agent_details.get('available_name') or agent_details.get('name') or agent_details.get('email')
                            assigned_agent_email = agent_details.get('email')
                            _logger.info('RR[HTTP] agente resuelto: name=%s email=%s', assigned_agent_name, assigned_agent_email)
                        else:
                            _logger.warning('RR[HTTP] NO se obtuvieron agent_details - agent_id=%s agent_email=%s',
                                            mapping_rec.chatwoot_agent_id, mapping_rec.chatwoot_agent_email)

                        mapping = {
                            'agent_id': mapping_rec.chatwoot_agent_id or None,
                            'agent_email': mapping_rec.chatwoot_agent_email or None,
                            'inbox_id': mapping_rec.chatwoot_inbox_id or None,
                            'prefer_assign_to_agent': mapping_rec.prefer_assign_to_agent,
                            'tags': [t.strip() for t in (mapping_rec.chatwoot_tags or '').split(',') if t.strip()],
                            'notify_message': (
                                f"Nuevo lead: {lead.id}"
                                f" - {data.get('solicitar_name') or data.get('name','Sin nombre')}"
                                f" - {data.get('solicitar_phone') or data.get('phone','')}"
                                + (f"\n👤 Ejecutivo asignado: {assigned_agent_name} ({assigned_agent_email})" if assigned_agent_name else '')
                            )
                        }
                        _logger.info('RR[HTTP] asignando conversación conv=%s account=%s mapping=%s',
                                     conversation_id_cw, account_id_cw, {
                                         'agent_id': mapping['agent_id'],
                                         'agent_email': mapping['agent_email'],
                                         'inbox_id': mapping['inbox_id'],
                                         'prefer_assign_to_agent': mapping['prefer_assign_to_agent'],
                                         'tags': mapping['tags'],
                                         'notify_message_len': len(mapping.get('notify_message', '')),
                                     })
                        result = env['chatwoot.client'].assign_conversation(account_id_cw, conversation_id_cw, mapping)
                        _logger.info('RR[HTTP] assign_conversation RESULTADO: %s', result)
                        ejecutivo = assigned_agent_name or mapping_rec.chatwoot_agent_email or 'sin datos'
                        if result.get('assigned_to') in ('agent', 'preserved'):
                            lead.sudo().message_post(body=f"Solicitud recibida. Ejecutivo asignado: {ejecutivo}")
                            _logger.info('RR[HTTP] chatter message posted: ejecutivo=%s', ejecutivo)
                        elif result.get('assigned_to') != 'existing':
                            lead.sudo().message_post(body=f"Solicitud recibida. Ejecutivo asignado: {ejecutivo}")
                            _logger.info('RR[HTTP] chatter message posted: ejecutivo=%s', ejecutivo)
                        else:
                            _logger.info('RR[HTTP][conv=%s]: assignee skipped, no chatter',
                                         conversation_id_cw)
                            ejecutivo = 'preservado'
                        try:
                            lead.sudo().write({
                                'chatwoot_conversation_id': str(conversation_id_cw),
                                'chatwoot_account_id': str(account_id_cw),
                                'chatwoot_processing_status': 'assigned' if result.get('ok', False) else 'error',
                                'chatwoot_processed_at': datetime.now(),
                                'chatwoot_assigned_agent_name': ejecutivo if result.get('ok', False) else False,
                                'chatwoot_assign_log': json.dumps({
                                    'assigned_to': result.get('assigned_to'),
                                    'assignee_id': result.get('assignee_id'),
                                    'mapping_id': mapping_rec.id,
                                    'agent_name': ejecutivo,
                                    'errors': result.get('errors', []),
                                    'warnings': result.get('warnings', []),
                                }),
                                'chatwoot_assign_failed': not result.get('ok', False),
                            })
                            _logger.info('RR[HTTP] lead %s escrito con estado=%s asignado_a=%s',
                                         lead.id, result.get('ok', False), result.get('assigned_to'))
                        except Exception as e_write:
                            _logger.warning('RR[HTTP] Error guardando chatwoot ids en lead %s: %s', lead.id, e_write)
                except Exception as e:
                    _logger.error("RR[HTTP] Error asignando a Chatwoot desde HTTP: %s", e, exc_info=True)
            else:
                _logger.warning('RR[HTTP] SKIP Chatwoot: faltan account_id(%s) o conversation_id(%s)',
                                account_id_cw, conversation_id_cw)
            _logger.info('RR[HTTP] FIN bloque Chatwoot')

            respuesta_bot = ChatBotUtils.generate_response(data, lead_id=lead.id, equipo_asignado=equipo_asignado, env=env)
            
            # Eliminación de sesión (opcional, comentado por seguridad)
            session_id = data.get('session_id')
            if session_id:
                try:
                    _logger.info("Intentando eliminar sesión: %s", session_id)
                    # session_record = env['chatbot.session'].search([('session_id', '=', session_id)], limit=1)
                    # if session_record:
                    #     session_record.unlink()
                    #     _logger.info("Sesión eliminada exitosamente: %s", session_id)
                except Exception as e:
                    _logger.error("Error al procesar sesión %s: %s", session_id, str(e), exc_info=True)
            
            response_data = {
                'session_id': data.get('session_id'),
                'conversation_id': data.get('conversation_id'),
                'account_id': data.get('account_id'),
                'existe': True,
                'lead_id': lead.id,
                'cliente_id': partner.id,
                'cliente_nombre': partner.name,
                'telefono': data.get('solicitar_phone'),
                'cedula': data.get('solicitar_vat'),
                'fecha_preferida': data.get('solicitar_fecha_preferida', ''),
                'hora_preferida': data.get('solicitar_hora_preferida', ''),
                'respuesta_para_bot': respuesta_bot,
                'text': respuesta_bot,
                'content': respuesta_bot,
                'output': respuesta_bot,
                'mensaje': 'Cita registrada exitosamente. Un ejecutivo se contactará pronto.',
                'session_eliminada': session_id if session_id else None,
                'equipo_asignado': equipo_asignado,
                'grupo_asignado': nombre_grupo
            }
            
            _logger.info("Cita creada exitosamente: Lead ID %s para cliente %s", lead.id, partner.name)
            return Response(
                json.dumps(response_data, default=str),
                content_type='application/json; charset=utf-8',
                headers=[('Access-Control-Allow-Origin', '*')]
            )
            
        except Exception as e:
            _logger.error("ERROR CREANDO CITA: %s", str(e), exc_info=True)
            return Response(
                json.dumps({'existe': False, 'error': True, 'mensaje': 'Error al crear la cita', 'detalle': str(e)}),
                status=500,
                content_type='application/json; charset=utf-8',
                headers=[('Access-Control-Allow-Origin', '*')]
            )
