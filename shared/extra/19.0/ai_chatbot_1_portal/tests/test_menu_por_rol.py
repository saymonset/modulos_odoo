from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.ai_chatbot_0_core.services.gpt_service import GptService

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "menu_por_rol")
class TestMenuPorRol(BaseChatbotTestCase):

    def setUp(self):
        super().setUp()
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
        """Sin IA, el men\u00fa usa etiquetas _MENU_LABELS + marca de la config."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio,costo')
        flujo_s = self._crear_flujo(
            'flujo_agendamiento_servicios', 'servicio,atenci\u00f3n')
        flujo_d = self._crear_flujo(
            'flujo_agendamiento_directo', 'cita,agendar,visita')
        config = self.env['chatbot.config'].create({
            'name': 'Fallback Test',
            'role': 'T\u00da ERES: Vendedor de prueba.',
            'flujo_ids': [(6, 0, [flujo_p.id, flujo_s.id, flujo_d.id])],
        })

        resultado = config._generar_menu_desde_flujos(config.flujo_ids)
        menu_texto = resultado['texto']

        self.assertTrue(menu_texto)
        self.assertEqual(resultado['modo'], 'fallback')
        self.assertIn('*Fallback Test*', menu_texto)
        self.assertTrue(menu_texto.startswith('*Fallback Test*'))
        self.assertIn('Precios y cotizaciones', menu_texto)
        self.assertIn('Servicios del negocio', menu_texto)
        self.assertIn('Agendar una cita o asesor\u00eda', menu_texto)
        self.assertIn('1\ufe0f\u20e3', menu_texto)
        self.assertIn('2\ufe0f\u20e3', menu_texto)
        self.assertIn('3\ufe0f\u20e3', menu_texto)

    def test_02_ia_genera_etiquetas_del_rol(self):
        """Con IA mockeada, el men\u00fa usa etiquetas del rol + marca en l\u00ednea 1."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio,costo')
        flujo_d = self._crear_flujo(
            'flujo_agendamiento_directo', 'cita,agendar')
        config = self.env['chatbot.config'].create({
            'name': 'Inmobiliaria Test',
            'role': 'T\u00da ERES: Vendedor de inmuebles comerciales.',
            'brand_name': 'Inmobiliaria XYZ',
            'flujo_ids': [(6, 0, [flujo_p.id, flujo_d.id])],
        })

        with patch.object(
            GptService, 'generar_menu_por_rol',
            return_value={
                'header': 'Tu asesor inmobiliario. \u00bfQu\u00e9 necesitas hoy?',
                'labels': {
                    'flujo_agendamiento_precios': 'Inmuebles y cotizaciones',
                    'flujo_agendamiento_directo': 'Agendar visita',
                },
            }):
            resultado = config._generar_menu_desde_flujos(config.flujo_ids)
            menu_texto = resultado['texto']

        self.assertTrue(menu_texto)
        self.assertEqual(resultado['modo'], 'ia')
        self.assertTrue(menu_texto.startswith('*Inmobiliaria XYZ*'))
        self.assertIn('Tu asesor inmobiliario. \u00bfQu\u00e9 necesitas hoy?', menu_texto)
        tagline_parte = menu_texto.split('\n')[1]
        self.assertNotIn('Inmobiliaria XYZ', tagline_parte)
        self.assertIn('Inmuebles y cotizaciones', menu_texto)
        self.assertIn('Agendar visita', menu_texto)
        self.assertNotIn('Precios y cotizaciones', menu_texto)
        self.assertNotIn('Servicios del negocio', menu_texto)
        self.assertIn('1\ufe0f\u20e3', menu_texto)
        self.assertIn('2\ufe0f\u20e3', menu_texto)

    def test_03_orden_misma_cantidad_opciones(self):
        """El men\u00fa tiene una opci\u00f3n por flujo, mismo orden que los flujos."""
        flujo_d = self._crear_flujo(
            'flujo_agendamiento_directo', 'cita,agendar')
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio,costo')
        config = self.env['chatbot.config'].create({
            'name': 'Orden Test',
            'flujo_ids': [(6, 0, [flujo_d.id, flujo_p.id])],
        })

        resultado = config._generar_menu_desde_flujos(config.flujo_ids)
        menu_texto = resultado['texto']

        pos_directo = menu_texto.index('Agendar una cita')
        pos_precios = menu_texto.index('Precios y cotizaciones')
        self.assertLess(pos_directo, pos_precios,
                        'El orden debe seguir el sorted(name) de los flujos')

    def test_04_boton_regenerar_menu(self):
        """El bot\u00f3n action_regenerar_menu actualiza el MENU output_largo."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'Boton Test',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        menu = self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'MENU',
            'prioridad': 10,
            'es_menu': True,
            'output_largo': 'Men\u00fa viejo',
        })

        result = config.action_regenerar_menu()

        self.assertEqual(result['params']['type'], 'warning')
        self.assertIn('men\u00fa con marca, sin tagline del rol',
                       result['params']['message'])
        menu.invalidate_recordset(['output_largo'])
        self.assertIn('*Boton Test*', menu.output_largo)
        self.assertIn('Precios y cotizaciones', menu.output_largo)
        self.assertNotEqual(menu.output_largo, 'Men\u00fa viejo')
        self.assertEqual(config.menu_generated_mode, 'fallback')
        self.assertTrue(config.menu_generated_at)

    def test_05_boton_sin_flujos_warning(self):
        """Sin flujo_ids, el bot\u00f3n devuelve warning."""
        config = self.env['chatbot.config'].create({
            'name': 'Sin Flujos Test',
        })
        result = config.action_regenerar_menu()
        self.assertEqual(result['params']['type'], 'warning')

    def test_06_boton_sin_menu_intention_warning(self):
        """Sin intenci\u00f3n MENU, el bot\u00f3n devuelve warning."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'Sin MENU Test',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        result = config.action_regenerar_menu()
        self.assertEqual(result['params']['type'], 'warning')

    def test_07_boton_ia_exitosa_escribe_modo_ia(self):
        """Con IA mockeada que retorna labels, el bot\u00f3n escribe mode='ia'."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'IA Test',
            'role': 'T\u00da ERES: Vendedor de prueba.',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'MENU',
            'prioridad': 10,
            'es_menu': True,
            'output_largo': 'Men\u00fa viejo',
        })

        with patch.object(
            GptService, 'generar_menu_por_rol',
            return_value={
                'header': 'Tu asesor. \u00bfQu\u00e9 necesitas hoy?',
                'labels': {'flujo_agendamiento_precios': 'Precios IA'},
            }):
            result = config.action_regenerar_menu()

        self.assertEqual(result['params']['type'], 'success')
        self.assertIn('IA', result['params']['message'])
        self.assertEqual(config.menu_generated_mode, 'ia')
        self.assertTrue(config.menu_generated_at)
        menu = self.env['chatbot.intencion'].search([
            ('config_id', '=', config.id), ('nombre', '=', 'MENU')
        ], limit=1)
        self.assertTrue(menu.output_largo.startswith('*IA Test*'))

    def test_08_stale_despues_de_editar(self):
        """Si se edita la config despu\u00e9s de generar, menu_stale = True."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'Stale Test',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'MENU',
            'prioridad': 10,
            'es_menu': True,
            'output_largo': 'Men\u00fa viejo',
        })

        config.action_regenerar_menu()
        self.assertFalse(config.menu_stale)

        config.write({'role': 'Nuevo rol'})
        self.assertTrue(config.menu_stale)

        config.action_regenerar_menu()
        self.assertFalse(config.menu_stale)

    def test_09_campos_vacios_sin_generar(self):
        """Sin generaci\u00f3n previa, los campos est\u00e1n vac\u00edos."""
        config = self.env['chatbot.config'].create({
            'name': 'Sin Generar Test',
        })
        self.assertFalse(config.menu_generated_mode)
        self.assertFalse(config.menu_generated_at)

    def test_10_marca_fallback_a_name(self):
        """Si brand_name vac\u00edo, la marca cae al name de la config."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'Solo Name',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })

        resultado = config._generar_menu_desde_flujos(config.flujo_ids)
        menu_texto = resultado['texto']

        self.assertTrue(menu_texto.startswith('*Solo Name*'))

    def test_11_marca_no_duplicada_en_ia(self):
        """El tagline IA no duplica la marca que Odoo antepone."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'No Dup Test',
            'brand_name': 'Mi Marca',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })

        with patch.object(
            GptService, 'generar_menu_por_rol',
            return_value={
                'header': 'Tu experto en soluciones. \u00bfQu\u00e9 necesitas hoy?',
                'labels': {'flujo_agendamiento_precios': 'Precios'},
            }):
            resultado = config._generar_menu_desde_flujos(config.flujo_ids)
            menu_texto = resultado['texto']

        self.assertEqual(menu_texto.count('*Mi Marca*'), 1)
        tagline = menu_texto.split('\n')[1]
        self.assertNotIn('Mi Marca', tagline)

    def test_12_sin_brand_name_usa_name(self):
        """Si brand_name vac\u00edo, la marca es el name de la config."""
        flujo_p = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'name': 'Negocio Sin Brand',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })

        resultado = config._generar_menu_desde_flujos(config.flujo_ids)
        menu_texto = resultado['texto']

        self.assertTrue(menu_texto)
        self.assertTrue(menu_texto.startswith('*Negocio Sin Brand*'))
        self.assertIn('\u00bfQu\u00e9 necesitas hoy?', menu_texto)
