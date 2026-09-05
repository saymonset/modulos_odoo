from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.ai_chatbot_0_core.services.gpt_service import GptService

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "menu_por_rol")
class TestMenuPorRol(BaseChatbotTestCase):

    def setUp(self):
        super().setUp()
        # Patch IA en el nivel de la clase (no depende de env.get)
        self.patch(
            GptService, 'generar_menu_por_rol',
            staticmethod(lambda *args, **kwargs: {}))

    def _crear_flujo(self, name, palabras_clave=''):
        return self.env['chatbot.flujo'].create({
            'name': name,
            'company_id': self.env.ref('base.main_company').id,
            'palabras_clave': palabras_clave,
        })

    def test_01_fallback_determinista_sin_ia(self):
        """Sin IA, el menú usa etiquetas _MENU_LABELS (regresión)."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio,costo')
        flujo_s = self._crear_flujo(
            'flujo_agendamiento_servicios', 'servicio,atención')
        flujo_d = self._crear_flujo(
            'flujo_agendamiento_directo', 'cita,agendar,visita')
        config = self.env['chatbot.config'].create({
            'name': 'Fallback Test',
            'role': 'TÚ ERES: Vendedor de prueba.',
            'flujo_ids': [(6, 0, [flujo_p.id, flujo_s.id, flujo_d.id])],
        })

        menu_texto = config._generar_menu_desde_flujos(config.flujo_ids)

        self.assertTrue(menu_texto)
        self.assertIn('Precios y cotizaciones', menu_texto)
        self.assertIn('Servicios del negocio', menu_texto)
        self.assertIn('Agendar una cita o asesoría', menu_texto)
        self.assertIn('1️⃣', menu_texto)
        self.assertIn('2️⃣', menu_texto)
        self.assertIn('3️⃣', menu_texto)

    def test_02_ia_genera_etiquetas_del_rol(self):
        """Con IA mockeada, el menú usa etiquetas del rol del negocio."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio,costo')
        flujo_d = self._crear_flujo(
            'flujo_agendamiento_directo', 'cita,agendar')
        config = self.env['chatbot.config'].create({
            'name': 'Inmobiliaria Test',
            'role': 'TÚ ERES: Vendedor de inmuebles comerciales.',
            'brand_name': 'Inmobiliaria XYZ',
            'flujo_ids': [(6, 0, [flujo_p.id, flujo_d.id])],
        })

        # Mockear la respuesta del gpt service a nivel de clase
        with patch.object(
            GptService, 'generar_menu_por_rol',
            return_value={
                'header': '¡Hola! Soy tu asesor inmobiliario.',
                'labels': {
                    'flujo_agendamiento_precios': 'Inmuebles y cotizaciones',
                    'flujo_agendamiento_directo': 'Agendar visita',
                },
            }):
            menu_texto = config._generar_menu_desde_flujos(config.flujo_ids)

        self.assertTrue(menu_texto)
        self.assertIn('¡Hola! Soy tu asesor inmobiliario.', menu_texto)
        self.assertIn('Inmuebles y cotizaciones', menu_texto)
        self.assertIn('Agendar visita', menu_texto)
        self.assertNotIn('Precios y cotizaciones', menu_texto)
        self.assertNotIn('Servicios del negocio', menu_texto)
        self.assertIn('1️⃣', menu_texto)
        self.assertIn('2️⃣', menu_texto)

    def test_03_orden_misma_cantidad_opciones(self):
        """El menú tiene una opción por flujo, mismo orden que los flujos."""
        flujo_d = self._crear_flujo(
            'flujo_agendamiento_directo', 'cita,agendar')
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio,costo')
        config = self.env['chatbot.config'].create({
            'name': 'Orden Test',
            'flujo_ids': [(6, 0, [flujo_d.id, flujo_p.id])],
        })

        menu_texto = config._generar_menu_desde_flujos(config.flujo_ids)

        # directo primero (alphabetical), precios después
        pos_directo = menu_texto.index('Agendar una cita')
        pos_precios = menu_texto.index('Precios y cotizaciones')
        self.assertLess(pos_directo, pos_precios,
                        'El orden debe seguir el sorted(name) de los flujos')

    def test_04_boton_regenerar_menu(self):
        """El botón action_regenerar_menu actualiza el MENU output_largo."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'Boton Test',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        # Crear intención MENU manualmente
        menu = self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'MENU',
            'prioridad': 10,
            'es_menu': True,
            'output_largo': 'Menú viejo',
        })

        result = config.action_regenerar_menu()

        self.assertEqual(result['params']['type'], 'success')
        menu.invalidate_recordset(['output_largo'])
        self.assertIn('Precios y cotizaciones', menu.output_largo)
        self.assertNotEqual(menu.output_largo, 'Menú viejo')

    def test_05_boton_sin_flujos_warning(self):
        """Sin flujo_ids, el botón devuelve warning."""
        config = self.env['chatbot.config'].create({
            'name': 'Sin Flujos Test',
        })
        result = config.action_regenerar_menu()
        self.assertEqual(result['params']['type'], 'warning')

    def test_06_boton_sin_menu_intention_warning(self):
        """Sin intención MENU, el botón devuelve warning."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'Sin MENU Test',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        result = config.action_regenerar_menu()
        self.assertEqual(result['params']['type'], 'warning')
