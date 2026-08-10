import json
import os

from odoo.tests import TransactionCase, tagged

WORKFLOW_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..', 'ai_chatbot_1_portal', 'n8n', 'chatbot_create_lead_0.json',
)


@tagged('odoo_chatwoot_connector', 'n8n_workflow')
class TestN8nWorkflow(TransactionCase):

    def _load_workflow(self):
        path = os.path.normpath(WORKFLOW_PATH)
        self.assertTrue(os.path.isfile(path), 'Workflow n8n no encontrado: %s' % path)
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)

    def test_nodo_obtener_configuracion_agente(self):
        data = self._load_workflow()
        nodes = {n['name']: n for n in data['nodes']}

        self.assertIn('Obtener_configuracion_agente', nodes)
        node = nodes['Obtener_configuracion_agente']
        params = node['parameters']
        self.assertEqual(params['method'], 'POST')
        self.assertTrue(params['url'].endswith('/ai_chatbot_1_portal/configuracion_agente'))
        self.assertIn('session_id', params['jsonBody'])
        self.assertTrue(node['type'].endswith('httpRequest'))

    def test_conexion_pasa_por_configuracion(self):
        data = self._load_workflow()
        conns = data['connections']

        self.assertEqual(
            conns['Consulta_o_agendar_cita']['main'][0][0]['node'],
            'Obtener_configuracion_agente',
        )
        self.assertEqual(
            conns['Obtener_configuracion_agente']['main'][0][0]['node'],
            'Agente_Informacion_basica',
        )

    def test_agente_usa_system_prompt_dinamico(self):
        data = self._load_workflow()
        nodes = {n['name']: n for n in data['nodes']}
        msg = nodes['Agente_Informacion_basica']['parameters']['options']['systemMessage']
        self.assertTrue(msg.startswith('={{ $json.system_prompt'))

    def test_js_code_respeta_flow_name_de_ia(self):
        data = self._load_workflow()
        nodes = {n['name']: n for n in data['nodes']}
        js = nodes['Separar_variables_en_json']['parameters']['jsCode']
        self.assertIn('flow_name || mapeoFlow[equipo] || flowPorDefecto', js)
        self.assertNotIn('resultado.flow_name = mapeoFlow[equipo] || flowPorDefecto', js)